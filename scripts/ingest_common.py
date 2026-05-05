"""Shared helpers for event ingestion scripts.

This module is imported by the per-source ingestion scripts in ``scripts/``
(``ingest_cmah.py``, ``ingest_ticketline.py``, ...). It contains everything
that is source-agnostic: dedup, YAML appending, name normalization.

Per-source scripts own their fetching and parsing logic and call into this
module for the common pieces.
"""
from __future__ import annotations

import datetime as dt
import html
import re
import unicodedata
import urllib.parse
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants shared across sources
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = REPO_ROOT / "_data" / "special_events.yml"
USER_AGENT = "TerceiraEventsBot/1.0 (+https://eventosterceira.pt)"
DESCRIPTION_MAX_CHARS = 500
DEFAULT_MAX_EVENTS = 20
LOOKAHEAD_DAYS = 365


# ---------------------------------------------------------------------------
# Name normalization + similarity
# ---------------------------------------------------------------------------

# Portuguese/English stopwords to ignore when comparing name similarity.
# Small, noisy function words that don't meaningfully distinguish events.
_DEDUP_STOPWORDS = frozenset(
    {
        "a", "o", "as", "os", "de", "do", "da", "dos", "das",
        "e", "em", "no", "na", "nos", "nas", "um", "uma",
        "the", "of", "and", "at", "in", "on", "for", "to",
    }
)


def normalize_name(name: str) -> str:
    """Normalize a name for dedup: lowercase, strip accents, unify dashes/quotes.

    HTML-unescapes in a loop so double-escaped entities like ``&amp;eacute;``
    (observed in Ticketline og:description payloads) round-trip correctly to
    the final character.
    """
    # Unescape until stable (handles double-escaping like &amp;eacute;)
    prev = None
    while prev != name:
        prev = name
        name = html.unescape(name)
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower()
    # Unify fancy quotes so "Foo" matches «Foo» (curly, guillemets, angle)
    name = re.sub(r"[\u00ab\u00bb\u2018\u2019\u201c\u201d\u2039\u203a\"']+", '"', name)
    # Unify dash variants (em, en, hyphen, minus, figure dash, ...) to a plain "-"
    name = re.sub(r"[\u2010-\u2015\u2212\-]+", "-", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _tokenize(name: str) -> frozenset[str]:
    """Extract non-stopword word tokens from a normalized name."""
    tokens = re.findall(r"\w+", normalize_name(name))
    return frozenset(t for t in tokens if t not in _DEDUP_STOPWORDS)


def is_similar_match(a_name: str, b_name: str) -> bool:
    """Return True if two event names look like the same event.

    Uses word-level set similarity on content tokens (stopwords stripped):

    - Jaccard |A∩B|/|A∪B| ≥ 0.6 catches near-identical names with small
      differences ("do Livro" vs "de livro", "Ready or Not 2 — O Ritual"
      vs "Ready or Not 2: O Ritual (2D)", etc).

    - Overlap coefficient |A∩B|/min(|A|,|B|) ≥ 0.8 catches asymmetric cases
      where one name is a short version and the other adds a long marketing
      suffix ("Concerto: Notas em Movimento" vs "Concerto: Notas em
      Movimento - quando a tradição encontra a energia académica").

    Requiring each input ≥3 content tokens AND ≥3 shared content tokens
    keeps false positives low on generic short names like "Cinema: X".
    """
    if normalize_name(a_name) == normalize_name(b_name):
        return True
    a_tokens = _tokenize(a_name)
    b_tokens = _tokenize(b_name)
    if len(a_tokens) < 3 or len(b_tokens) < 3:
        return False
    shared = a_tokens & b_tokens
    if len(shared) < 3:
        return False
    union = a_tokens | b_tokens
    jaccard = len(shared) / len(union)
    if jaccard >= 0.6:
        return True
    overlap = len(shared) / min(len(a_tokens), len(b_tokens))
    return overlap >= 0.8


# ---------------------------------------------------------------------------
# Description cleanup
# ---------------------------------------------------------------------------


def clean_description(text: str, *, max_chars: int = DESCRIPTION_MAX_CHARS) -> str:
    """Unescape iCal, decode HTML entities (recursively), strip tags, collapse, truncate.

    Recursive unescape handles cases like Ticketline's og:description which
    is double-escaped — ``&amp;eacute;`` should become ``é``, not ``&eacute;``.
    """
    if not text:
        return ""
    # iCal escape sequences (harmless no-ops if the input isn't iCal)
    text = (
        text.replace("\\n", " ")
        .replace("\\N", " ")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )
    # Repeated HTML entity decode (handles &amp;eacute; → &eacute; → é)
    prev = None
    while prev != text:
        prev = text
        text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        truncated = text[:max_chars].rsplit(" ", 1)[0]
        text = truncated + "…"
    return text


# ---------------------------------------------------------------------------
# Dedup index over existing YAML
# ---------------------------------------------------------------------------


def load_existing_yaml(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        raise ValueError(
            f"{path}: expected a top-level YAML list, got {type(data).__name__}"
        )
    return data


def build_dedup_index(
    existing: list[dict],
) -> tuple[dict[dt.date, list[str]], set[str]]:
    """Build a dedup index from existing events.

    Returns:
      - date_to_names: map of date → list of raw names on that date
        (normalization happens inside is_similar_match).
      - source_uids: set of source UIDs already present.
    """
    date_to_names: dict[dt.date, list[str]] = {}
    source_uids: set[str] = set()
    for ev in existing:
        if not isinstance(ev, dict):
            continue
        name = ev.get("name")
        date = ev.get("date")
        if name and isinstance(date, dt.date):
            date_to_names.setdefault(date, []).append(str(name))
        sid = ev.get("source_uid")
        if sid:
            source_uids.add(str(sid))
    return date_to_names, source_uids


def matches_existing(
    candidate_name: str,
    candidate_date: dt.date,
    date_to_names: dict[dt.date, list[str]],
) -> bool:
    for existing_name in date_to_names.get(candidate_date, []):
        if is_similar_match(candidate_name, existing_name):
            return True
    return False


# ---------------------------------------------------------------------------
# YAML text-append formatting
# ---------------------------------------------------------------------------


def yaml_double_quote(s: str) -> str:
    """Double-quote a string for YAML, escaping backslashes and quotes."""
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


_BARE_UNSAFE = re.compile(r"""[:#'"\\{}\[\],&*!|>%@`]""")


def yaml_value(s: str) -> str:
    """Return a YAML scalar representation, quoting when needed."""
    if s is None or s == "":
        return '""'
    if _BARE_UNSAFE.search(s):
        return yaml_double_quote(s)
    if s.startswith(("-", "?", "!")) or s != s.strip():
        return yaml_double_quote(s)
    return s


def format_event_yaml(event: dict) -> str:
    """Hand-format a single event as a YAML list item matching the file style."""
    out: list[str] = []
    out.append(f"- date: {event['date'].isoformat()}")
    out.append(f"  name: {yaml_double_quote(event['name'])}")
    out.append(f"  venue: {yaml_value(event['venue'])}")
    if event.get("address"):
        out.append(f"  address: {yaml_value(event['address'])}")
    if event.get("map_url"):
        out.append(f"  map_url: {event['map_url']}")
    if event.get("time"):
        out.append(f'  time: "{event["time"]}"')
    if event.get("description"):
        out.append(f"  description: {yaml_double_quote(event['description'])}")
    if event.get("source_url"):
        out.append(f"  source_url: {event['source_url']}")
    if event.get("source_uid"):
        out.append(f'  source_uid: "{event["source_uid"]}"')
    if event.get("tags"):
        out.append("  tags:")
        for t in event["tags"]:
            out.append(f"  - {t}")
    return "\n".join(out) + "\n"


def build_map_url(venue: str, locality: str = "Angra do Heroísmo") -> str:
    """Return a Google Maps search URL for a venue.

    Locality defaults to Angra do Heroísmo (CMAH's entire feed is scoped to
    that city) but can be overridden for venues in Praia da Vitória or
    elsewhere on Terceira.
    """
    query = urllib.parse.quote(f"{venue} {locality}".strip())
    return f"https://www.google.com/maps/search/?api=1&query={query}"
