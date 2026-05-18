#!/usr/bin/env python3
"""Ingest Terceira's tourada à corda season calendar into _data/special_events.yml.

Tourada à corda (bull-on-a-rope) is the rope-tethered street bullfighting
that runs every year on Terceira from May to October. Each freguesia
(parish) organises its own dates, so there's no single canonical feed; the
closest we have are:

  - the regional government announcement listing all approved dates for the
    season (published by Direção Regional de Cultura early in the year),
  - the two municipalities' own event listings (already covered by
    ingest_cmah.py and ingest_cmpv.py for events they're hosting), and
  - individual junta de freguesia websites which post their parish's
    dates well in advance.

This script targets the **junta de freguesia** layer. Each entry in
JUNTA_SOURCES is a parish website that historically publishes its
touradas calendar as a list/page we can scrape for date+venue. The
scrape is intentionally lenient: we look for date patterns in the HTML
of a known calendar page and emit one event per match.

If a junta page changes layout or 404s, the corresponding source is
skipped — the cron exits cleanly and other parishes still get ingested.

To add a parish:
  1. Find their bullfighting calendar URL.
  2. Append a JuntaSource to JUNTA_SOURCES with the URL + display name +
     address template.
  3. The script handles the rest.

Dedup uses the same `(date, name)` similarity check as the other ingests,
so re-runs and overlap with CMAH/CMPV are safe.
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from ingest_common import (
    DEFAULT_MAX_EVENTS,
    LOOKAHEAD_DAYS,
    USER_AGENT,
    YAML_PATH,
    build_dedup_index,
    build_map_url,
    format_event_yaml,
    load_existing_yaml,
    matches_existing,
)

logger = logging.getLogger("ingest_touradas")


@dataclass(frozen=True)
class JuntaSource:
    """A parish website that publishes a bullfighting calendar."""

    slug: str               # used in source_uid; usually the parish slug
    calendar_url: str
    freguesia: str          # parish display name (e.g. "Porto Judeu")
    venue: str              # default venue/locality (e.g. "Rossio, Porto Judeu")
    address: str            # full street address
    map_url: str = ""       # filled from build_map_url when blank


# Starter list. Add parishes here as their calendar pages become known.
# Sources picked are parishes that historically host multiple dates per
# season (the freguesias with active commissions and confirmed dates).
JUNTA_SOURCES: list[JuntaSource] = [
    JuntaSource(
        slug="porto-judeu",
        calendar_url="https://www.portojudeu.pt/",
        freguesia="Porto Judeu",
        venue="Rossio, Porto Judeu",
        address="Rossio, 9700-368 Porto Judeu",
    ),
    JuntaSource(
        slug="terra-cha",
        calendar_url="https://www.juntafterracha.com/",
        freguesia="Terra Chã",
        venue="Terreiro, Terra Chã",
        address="Terreiro, 9700 Terra Chã",
    ),
]

# Match a Portuguese day-month line, e.g. "15 de maio", "23 de Junho",
# "07/06/2026", "07-06-2026". Strict enough that ordinary prose doesn't
# generate false-positive events.
PT_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}
LONG_DATE_RE = re.compile(
    r"\b(?P<day>\d{1,2})\s+de\s+(?P<month>"
    + "|".join(PT_MONTHS.keys())
    + r")(?:\s+de\s+(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)
NUMERIC_DATE_RE = re.compile(
    r"\b(?P<day>\d{1,2})[/-](?P<month>\d{1,2})[/-](?P<year>\d{4})\b"
)
# Tourada-specific keywords that must appear in the same line/paragraph
# as the date for it to be considered a bullfighting event.
TOURADA_KEYWORDS_RE = re.compile(
    r"\b(tourada|touradas|toirada|toiradas|bezerrada|garraio)\b", re.IGNORECASE
)
# A "ganadeiro" attribution (the cattle-breeder identifier) often
# follows the date. Extract it when present — it's the one detail
# attendees care about.
GANADEIRO_RE = re.compile(
    r"\b(?:ganadeiro|ganadeiros)\s*[:\-]?\s*([A-Za-zÀ-ÿ &.,'\-]{2,80})", re.IGNORECASE
)


def _fetch(url: str, timeout: int = 30) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except Exception as e:  # noqa: BLE001
        logger.warning("fetch failed for %s: %s", url, e)
        return None
    return raw.decode("utf-8", errors="replace")


def _strip_tags(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _candidate_dates(text: str, today: dt.date) -> list[tuple[dt.date, int, int]]:
    """Find (date, match_start, match_end) hits in `text`.

    Year defaults to the current year when omitted. Drops dates in the past
    (relative to `today`) so re-runs don't keep re-suggesting last season.
    """
    found: list[tuple[dt.date, int, int]] = []
    for m in LONG_DATE_RE.finditer(text):
        day = int(m.group("day"))
        month = PT_MONTHS[m.group("month").lower()]
        year = int(m.group("year")) if m.group("year") else today.year
        try:
            date = dt.date(year, month, day)
        except ValueError:
            continue
        if date < today:
            continue
        found.append((date, m.start(), m.end()))
    for m in NUMERIC_DATE_RE.finditer(text):
        try:
            date = dt.date(int(m.group("year")), int(m.group("month")), int(m.group("day")))
        except ValueError:
            continue
        if date < today:
            continue
        found.append((date, m.start(), m.end()))
    return found


def _nearby_window(text: str, start: int, end: int, radius: int = 240) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)]


def harvest_junta(source: JuntaSource, today: dt.date) -> list[dict]:
    html = _fetch(source.calendar_url)
    if not html:
        return []
    text = _strip_tags(html)

    events: list[dict] = []
    for date, start, end in _candidate_dates(text, today):
        window = _nearby_window(text, start, end)
        if not TOURADA_KEYWORDS_RE.search(window):
            continue
        ganadeiro = None
        gm = GANADEIRO_RE.search(window)
        if gm:
            ganadeiro = gm.group(1).strip().rstrip(".,;")

        name = f"Tourada à Corda — {source.venue}"
        description_bits = [
            "Tourada à corda — tradicional tourada de rua com toiro preso por uma corda.",
        ]
        if ganadeiro:
            description_bits.append(f"Ganadeiro: {ganadeiro}.")
        description = " ".join(description_bits)

        events.append(
            {
                "date": date,
                "name": name,
                "venue": source.venue,
                "address": source.address,
                "map_url": source.map_url or build_map_url(source.venue, "Praia da Vitória"
                                                            if "Praia" in source.address else
                                                            "Angra do Heroísmo"),
                "time": None,
                "description": description,
                "source_url": source.calendar_url,
                "source_uid": f"{source.slug}-{date.isoformat()}@touradas",
                "tags": ["bullfighting", "outdoor"],
            }
        )
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--max-events", type=int, default=DEFAULT_MAX_EVENTS,
        help="Max events to add per invocation (default: %(default)s)",
    )
    parser.add_argument("--yaml-path", type=Path, default=YAML_PATH)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    today = dt.date.today()
    lookahead = today + dt.timedelta(days=LOOKAHEAD_DAYS)

    all_raw: list[dict] = []
    for source in JUNTA_SOURCES:
        try:
            harvested = harvest_junta(source, today)
        except Exception as e:  # noqa: BLE001
            logger.warning("source %s blew up: %s — skipping", source.slug, e)
            continue
        logger.info("source %s: %d candidate dates", source.slug, len(harvested))
        all_raw.extend(harvested)

    if not all_raw:
        logger.info("no touradas discovered — exiting cleanly")
        return 0

    existing = load_existing_yaml(args.yaml_path)
    date_to_names, source_uids = build_dedup_index(existing)

    candidates: list[dict] = []
    skipped_dedup = 0
    skipped_window = 0
    seen_uid_within_run: set[str] = set()
    for event in all_raw:
        if event["date"] > lookahead:
            skipped_window += 1
            continue
        if event["source_uid"] in source_uids or event["source_uid"] in seen_uid_within_run:
            skipped_dedup += 1
            continue
        if matches_existing(event["name"], event["date"], date_to_names):
            skipped_dedup += 1
            continue
        seen_uid_within_run.add(event["source_uid"])
        candidates.append(event)

    logger.info(
        "found %d new candidate events (skipped %d dedup, %d out-of-window)",
        len(candidates), skipped_dedup, skipped_window,
    )

    if not candidates:
        return 0

    candidates.sort(key=lambda e: e["date"])
    if len(candidates) > args.max_events:
        logger.warning("capping %d → %d", len(candidates), args.max_events)
        candidates = candidates[: args.max_events]

    block = f"\n# Auto-ingested touradas ({today.isoformat()})\n"
    for ev in candidates:
        block += format_event_yaml(ev) + "\n"

    if args.dry_run:
        sys.stdout.write(block)
        logger.info("[dry-run] would add %d events", len(candidates))
        return 0

    with args.yaml_path.open("a", encoding="utf-8") as f:
        f.write(block)
    logger.info("added %d events to %s", len(candidates), args.yaml_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
