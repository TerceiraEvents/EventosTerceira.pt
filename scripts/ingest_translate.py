"""Translate ingested event titles and descriptions into the other locale.

The ingest sources publish a single language (Portuguese, except Visit
Azores which lists in English) while ``test_event_locales.py`` requires
both locales per event. This module calls an OpenAI-compatible
chat-completions endpoint, configured by the environment variables in
``ENV_VARS``, for the missing language and stores it in the explicit
``_en`` / ``_pt`` sibling field; the bare ``name`` / ``description``
keeps the source text. Translation failures never abort ingestion —
they surface as health warnings and the locale gate stays red until a
curator fills the gap.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

ENV_VARS = ("TRANSLATION_API_URL", "TRANSLATION_API_KEY", "TRANSLATION_MODEL")
BATCH_SIZE = 10          # events per request
FIELDS = ("name", "description")
LANGUAGES = {"pt": "European Portuguese", "en": "English"}
SYSTEM_PROMPT = (
    "You translate event listings from Terceira, Azores, from {source} into {target} "
    "for a community events website. Translate each string faithfully and completely: "
    "keep every fact, date, time, price, emoji and punctuation mark, including a trailing "
    "ellipsis; add nothing and omit nothing. Keep proper names exactly as published: people, "
    "bands and groups, venues, parishes, towns and other place names (for example Porto Judeu, "
    "Praia da Vitória, Terra Chã, Angra do Heroísmo), organisations, and titles of works and "
    "brands. Translate the descriptive words around them (for example Feira, Mercado de Natal, "
    "Hora do Conto, Entrada livre). Reply with a JSON object {{\"translations\": [...]}} holding "
    "exactly one translated string per input string, in the same order."
)


class TranslationError(RuntimeError):
    """The translation request failed or returned unusable data."""


def chat_completions_translate(texts: list[str], source: str, target: str) -> list[str]:
    """Translate ``texts`` from ``source`` into ``target`` via chat completions.

    Returns one translated string per input, in order. Raises
    TranslationError when the endpoint is not configured, the request
    fails, or the response does not hold exactly one non-empty string
    per input.
    """
    missing = [name for name in ENV_VARS if not os.environ.get(name)]
    if missing:
        raise TranslationError(f"translation is not configured: set {', '.join(missing)}")
    payload = {
        "model": os.environ["TRANSLATION_MODEL"],
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system",
             "content": SYSTEM_PROMPT.format(source=LANGUAGES[source], target=LANGUAGES[target])},
            {"role": "user",
             "content": json.dumps({"strings": texts}, ensure_ascii=False)},
        ],
    }
    request = urllib.request.Request(
        os.environ["TRANSLATION_API_URL"],
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {os.environ['TRANSLATION_API_KEY']}",
                 "Content-Type": "application/json",
                 "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            content = json.loads(response.read())["choices"][0]["message"]["content"]
        translations = json.loads(content)["translations"]
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError,
            KeyError, IndexError, TypeError, ValueError) as exc:
        raise TranslationError(f"Translation request failed: {exc}") from exc
    if not isinstance(translations, list) or len(translations) != len(texts):
        count = len(translations) if isinstance(translations, list) else "no"
        raise TranslationError(
            f"Translation endpoint returned {count} translations for {len(texts)} inputs")
    if any(not isinstance(t, str) or not t.strip() for t in translations):
        raise TranslationError("Translation endpoint returned an empty translation")
    return translations


def translate_events(events: list[dict], source: str, translate=None) -> list[str]:
    """Fill the missing-language ``_en``/``_pt`` siblings on ``events``.

    The bare ``name``/``description`` keeps the ``source``-language text;
    the translation goes into the explicit sibling field. Returns one
    warning string per failed chunk; failures leave events untranslated
    so ingestion continues and the locale gate reports the gap.
    """
    translate = translate or chat_completions_translate
    target = "en" if source == "pt" else "pt"
    warnings: list[str] = []
    for start in range(0, len(events), BATCH_SIZE):
        chunk = events[start:start + BATCH_SIZE]
        jobs = [(event, field) for event in chunk for field in FIELDS
                if isinstance(event.get(field), str) and event[field].strip()
                and not event.get(f"{field}_{target}")]
        if not jobs:
            continue
        try:
            results = translate([event[field] for event, field in jobs], source, target)
        except TranslationError as exc:
            names = ", ".join(sorted({event.get("name", "?") for event, _ in jobs}))
            warning = (f"Translation {source}->{target} failed for {len(jobs)} fields "
                       f"({names}): {exc}")
            logging.warning(warning)
            warnings.append(warning)
            continue
        for (event, field), value in zip(jobs, results):
            event[f"{field}_{target}"] = value.strip()
    return warnings
