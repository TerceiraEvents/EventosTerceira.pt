"""Shared helpers for event ingestion scripts.

This module is imported by the per-source ingestion scripts in ``scripts/``
(``ingest_cmah.py``, ``ingest_ticketline.py``, ...). It contains everything
that is source-agnostic: dedup, YAML appending, name normalization.

Per-source scripts own their fetching and parsing logic and call into this
module for the common pieces.
"""
from __future__ import annotations

import datetime as dt
import functools
import html
import os
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
VENUE_LOCALITIES_PATH = REPO_ROOT / "_data" / "venue_localities.yml"
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


# Generic event-type labels that sources put before a title ("Cinema: Verity")
# while other sources publish the bare title ("VERITY").
_CATEGORY_LABELS = frozenset(
    {
        "cinema", "concerto", "conferencia", "danca", "exposicao",
        "festival", "formacao", "palestra", "teatro", "workshop",
    }
)

# Words that join a title to its subject in English and Portuguese ("Ocean
# with David Attenborough", "Ocean com David Attenborough"); ignored when one
# title is compared with the words of another.
_CONNECTOR_WORDS = frozenset({"com", "with"})

# Locality values a record or venue alias may carry (``locality`` in
# ``_data/special_events.yml``, ``_data/venue_localities.yml``).
_KNOWN_LOCALITIES = frozenset({"angra", "praia", "other"})


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


def _words(text: str) -> str:
    """Join the alphanumeric runs of a normalized title with single spaces."""
    return " ".join(re.findall(r"[^\W_]+", text))


def _split_category_label(name: str) -> tuple[str | None, str]:
    """Split a leading event-type label ("Cinema: ") from a title.

    The second item is the title's words: normalized, with every
    non-alphanumeric character (punctuation, quotes, dashes) reduced to a
    single space.
    """
    label, separator, rest = normalize_name(name).partition(":")
    if separator and label.strip() in _CATEGORY_LABELS and rest.strip():
        return label.strip(), _words(rest)
    return None, _words(normalize_name(name))


def same_title(a_name: str, b_name: str) -> bool:
    """Return True if two titles are equal once case, accents and punctuation are ignored.

    A leading event-type label is ignored on one side or both, but two
    different labels ("Concerto: X", "Cinema: X") are different titles.
    """
    (a_label, a_core), (b_label, b_core) = _split_category_label(a_name), _split_category_label(b_name)
    return bool(a_core) and a_core == b_core and (a_label is None or b_label is None or a_label == b_label)


def is_contained_title(a_name: str, b_name: str, minimum: int = 3) -> bool:
    """Return True if every content word of one title is in the other.

    Content words are the title's words without stopwords, connector words
    ("com", "with") and a leading event-type label; order and repetition are
    ignored. At least ``minimum`` words must be contained, so the rule matches
    "Cinema: Ocean with David Attenborough" with "“Ocean” com David
    Attenborough regressa à ilha Terceira" and never a one- or two-word title.
    Two different event-type labels are different titles. A title may also be
    compared by the words after its first colon ("Mesa redonda: Para Lá das
    Colunas de Hércules" is contained in "Para lá das Colunas de Hércules: a
    descoberta dos Açores"), which drops a series name or label that the other
    title does not repeat.
    """
    (a_label, a_core), (b_label, b_core) = _split_category_label(a_name), _split_category_label(b_name)
    if a_label is not None and b_label is not None and a_label != b_label:
        return False
    skipped = _DEDUP_STOPWORDS | _CONNECTOR_WORDS

    def content(text: str) -> frozenset[str]:
        return frozenset(text.split()) - skipped

    a_words, b_words = content(a_core), content(b_core)
    smaller, larger = sorted((a_words, b_words), key=len)
    if len(smaller) >= minimum and smaller <= larger:
        return True
    for name, other_words in ((a_name, b_words), (b_name, a_words)):
        _, colon, subtitle = normalize_name(name).partition(":")
        words = content(_words(subtitle))
        if colon and len(words) >= minimum and words <= other_words:
            return True
    return False


def start_time(value) -> str | None:
    """Return the ``HH:MM`` a time field starts at, or None ("15:00–18:00" starts at 15:00)."""
    match = re.match(r"\s*(\d{1,2})[:h](\d{2})", str(value or ""))
    return f"{int(match.group(1)):02d}:{match.group(2)}" if match else None


@functools.lru_cache(maxsize=None)
def _locality_aliases(path: Path) -> tuple[tuple[str, str], ...]:
    with path.open("r", encoding="utf-8") as f:
        venues = yaml.safe_load(f)
    return tuple(
        (normalize_name(alias), venue["locality"])
        for venue in venues
        for alias in venue.get("aliases", [])
    )


def venue_locality(venue: str | None, locality: str | None = None) -> str | None:
    """Return the locality of a record or venue string, or None when it is not known.

    A record's own ``locality`` wins. Otherwise a venue that contains exactly
    one locality's alias from ``_data/venue_localities.yml`` takes that locality.
    """
    if locality in _KNOWN_LOCALITIES:
        return locality
    text = normalize_name(str(venue or ""))
    found = {place for alias, place in _locality_aliases(VENUE_LOCALITIES_PATH) if alias and alias in text}
    return found.pop() if len(found) == 1 else None


def venues_in_conflict(event: dict, other: dict) -> bool:
    """Return True if both records name venues in two different known localities."""
    place = venue_locality(event.get("venue"), event.get("locality"))
    other_place = venue_locality(other.get("venue"), other.get("locality"))
    return place is not None and other_place is not None and place != other_place


def same_start_time(event: dict, other: dict) -> bool:
    """Return True if both records state a start time and it is the same."""
    time = start_time(event.get("time"))
    return time is not None and time == start_time(other.get("time"))


NAME_KEYS = ("name", "name_en", "name_pt")


def same_instant(event: dict, other: dict) -> bool:
    """Return True if two records have the same title and start time.

    The caller has already checked that ``event`` falls on a day ``other``
    covers; neither the venue nor the language of the description matters.
    """
    return same_start_time(event, other) and any(
        same_title(event["name"], other.get(key) or "") for key in NAME_KEYS
    )


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

    Short titles cannot reach those thresholds, so two names also match when
    they are the same title (``same_title``): identical once case, accents,
    punctuation and a leading event-type label are ignored ("ROMANCE À
    ITALIANA" and "Cinema: Romance à Italiana"). Two different labels on the
    same title ("Concerto: X", "Cinema: X") do not match.
    """
    if normalize_name(a_name) == normalize_name(b_name) or same_title(a_name, b_name):
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
        date = ev.get("date")
        if isinstance(date, dt.date):
            for key in NAME_KEYS:
                if ev.get(key):
                    date_to_names.setdefault(date, []).append(str(ev[key]))
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


def listing_kind(tags: list[str] | None, date: dt.date, end_date: dt.date | None) -> str | None:
    """Classify only tagged listings whose published period spans multiple days."""
    if "exhibition" in (tags or []) and end_date is not None and end_date > date:
        return "exhibition"
    return None


def yaml_double_quote(s: str) -> str:
    """Double-quote a string for YAML, escaping quotes and control characters."""
    out = []
    for ch in s:
        if ch in '\\"':
            out.append("\\" + ch)
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20 or 0x7F <= ord(ch) <= 0x9F or ch in "\u2028\u2029":
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    return f'"{"".join(out)}"'


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
    if event.get("end_date") and event["end_date"] > event["date"]:
        out.append(f"  end_date: {event['end_date'].isoformat()}")
    kind = listing_kind(event.get("tags"), event["date"], event.get("end_date"))
    if kind:
        out.append(f"  kind: {kind}")
    out.append(f"  name: {yaml_double_quote(event['name'])}")
    for locale in ("en", "pt"):
        if event.get(f"name_{locale}"):
            out.append(f"  name_{locale}: {yaml_double_quote(event[f'name_{locale}'])}")
    out.append(f"  venue: {yaml_value(event['venue'])}")
    if event.get("address"):
        out.append(f"  address: {yaml_value(event['address'])}")
    if event.get("map_url"):
        out.append(f"  map_url: {event['map_url']}")
    if event.get("time"):
        out.append(f'  time: "{event["time"]}"')
    if event.get("description"):
        out.append(f"  description: {yaml_double_quote(event['description'])}")
        for locale in ("en", "pt"):
            if event.get(f"description_{locale}"):
                out.append(f"  description_{locale}: {yaml_double_quote(event[f'description_{locale}'])}")
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


def append_events_block(path: Path, block: str, added: int) -> None:
    """Append ``block`` to the event list at ``path`` after checking it parses.

    Raises ValueError, leaving the file untouched, when the combined YAML is
    not a list that grew by ``added`` records.
    """
    original = path.read_text(encoding="utf-8")
    output = original + block
    before = yaml.safe_load(original) or []
    try:
        after = yaml.safe_load(output)
    except yaml.YAMLError as exc:
        raise ValueError(f"Generated YAML does not parse: {exc}") from exc
    if not isinstance(after, list) or len(after) != len(before) + added:
        raise ValueError("Generated YAML does not preserve the existing event list")
    path.write_text(output, encoding="utf-8")


def report_warnings(source: str, warnings: list[str]) -> None:
    """Show ingest warnings in the Actions job summary when one is available."""
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if warnings and summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(f"### {source}: translation warnings\n\n"
                         + "".join(f"- {w}\n" for w in warnings))
