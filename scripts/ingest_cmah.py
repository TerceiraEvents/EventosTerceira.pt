#!/usr/bin/env python3
"""Ingest events from the CMAH iCal feed into _data/special_events.yml.

Source: https://angradoheroismo.pt/events.ics

This script only ADDS new events. It never modifies existing entries.
Dedup keys:
  1. `source_uid` (iCal UID) — catches re-runs of the same event.
  2. Normalized `(name, date)` tuple — catches events previously added manually.

Run with --dry-run to preview without modifying the file.
Run with --max-events N to cap additions per invocation (default: 20).

The script is text-append-based: it parses the YAML only for dedup, and
appends new entries as hand-formatted text. This preserves the file's
existing comments, quoting, and section headers.
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
import urllib.request
from pathlib import Path

import icalendar

from ingest_common import (
    DEFAULT_MAX_EVENTS,
    LOOKAHEAD_DAYS,
    USER_AGENT,
    YAML_PATH,
    build_dedup_index,
    build_map_url,
    clean_description,
    format_event_yaml,
    load_existing_yaml,
    matches_existing,
    normalize_name,
)

CMAH_ICAL_URL = "https://angradoheroismo.pt/events.ics"

# Conservative CMAH category → tag slug mapping. Anything not in this map is
# left untagged rather than guessed at. Keep tag slugs in sync with
# _data/event_tags.yml.
CATEGORY_TAG_MAP = {
    "Cinema": "cinema",
    "Exposições": "exhibition",
    "Exposição": "exhibition",
    "Música": "live-music",
    "Concertos": "live-music",
    "Concerto": "live-music",
    "Conferências e Literatura": "literature",
    "Literatura": "literature",
    "Livros": "literature",
    "Teatro": "theater",
    "Dança": "dance",
    "Festas Tradicionais e Touradas": "bullfighting",
    "Festas Tradicionais eTouradas": "bullfighting",  # CMAH typo seen in feed
    "Formações": "workshop",
    "Workshop": "workshop",
    "Workshops": "workshop",
    "Gastronomia": "food-drink",
    "Ar livre": "outdoor",
    "Família": "kid-friendly",
    "Infantil": "kid-friendly",
}

# An event whose DTEND falls the next morning at or before this time ends
# after midnight rather than on a second day.
OVERNIGHT_END_LIMIT = dt.time(6, 0)

logger = logging.getLogger("ingest_cmah")


# ---------------------------------------------------------------------------
# CMAH-specific fetching + parsing
# ---------------------------------------------------------------------------


def fetch_ical(url: str) -> icalendar.Calendar:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    return icalendar.Calendar.from_ical(data)


def extract_date_time(prop) -> tuple[dt.date, str | None]:
    """Return (date, HH:MM or None) from a DTSTART property.

    iCal DATE-only values (VALUE=DATE) come back as timezone-aware datetimes
    at midnight; we detect those via the VALUE parameter and strip the time.
    A start at local midnight is the feed's way of publishing a date without
    a time, so it yields no time either.
    """
    value = prop.dt
    value_param = prop.params.get("VALUE") if hasattr(prop, "params") else None
    if value_param == "DATE":
        if isinstance(value, dt.datetime):
            return (value.date(), None)
        return (value, None)
    if isinstance(value, dt.datetime):
        time = value.strftime("%H:%M")
        return (value.date(), None if time == "00:00" else time)
    if isinstance(value, dt.date):
        return (value, None)
    raise ValueError(f"unexpected DTSTART type: {type(value).__name__}")


def extract_end_date(start_prop, end_prop) -> dt.date | None:
    """Return the last day of a multi-day event from DTSTART and DTEND, or None.

    - A DTEND of VALUE=DATE is exclusive (RFC 5545), so its last day is the
      day before.
    - A timed DTEND ends on its own date, including a midnight DTEND: the
      feed publishes "18 to 22 November" as 00:00 on the 18th to 00:00 on
      the 22nd.
    - A DTEND on the next day before 06:00 and earlier than the start's clock
      time is an event that runs past midnight (22:00 to 02:00), not a second
      day.
    """
    if end_prop is None:
        return None
    start, end = start_prop.dt, end_prop.dt
    start_day = start.date() if isinstance(start, dt.datetime) else start
    if end_prop.params.get("VALUE") == "DATE":
        end_day = (end.date() if isinstance(end, dt.datetime) else end) - dt.timedelta(days=1)
    elif isinstance(end, dt.datetime):
        if isinstance(start, dt.datetime) and start.tzinfo and end.tzinfo:
            end = end.astimezone(start.tzinfo)
        end_day = end.date()
        if (
            isinstance(start, dt.datetime)
            and end_day == start_day + dt.timedelta(days=1)
            and end.time() < start.time()
            and end.time() <= OVERNIGHT_END_LIMIT
        ):
            return None
    else:
        end_day = end
    return end_day if end_day > start_day else None


def parse_location(loc: str) -> tuple[str, str]:
    """Split a CMAH LOCATION string into (venue, address).

    CMAH format: "Venue Name, Street, Angra do Heroísmo, Ilha Terceira,
                  9700-xxx, Região Autónoma dos Açores, Portugal"
    """
    if not loc:
        return ("", "")
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    if not parts:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    venue = parts[0]
    # Drop generic regional trailers to keep addresses short and legible.
    drop = {"Portugal", "Região Autónoma dos Açores", "Ilha Terceira"}
    address = ", ".join(p for p in parts[1:] if p not in drop)
    return (venue, address)


def map_tags(categories) -> list[str]:
    if categories is None:
        return []
    if hasattr(categories, "cats"):
        cats = [str(c) for c in categories.cats]
    elif isinstance(categories, (list, tuple)):
        cats = [str(c) for c in categories]
    else:
        cats = [str(categories)]
    tags: list[str] = []
    for c in cats:
        slug = CATEGORY_TAG_MAP.get(c.strip())
        if slug and slug not in tags:
            tags.append(slug)
    return tags


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be added without modifying the file",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=DEFAULT_MAX_EVENTS,
        help="Max events to add per invocation (default: %(default)s)",
    )
    parser.add_argument("--url", default=CMAH_ICAL_URL, help="iCal feed URL")
    parser.add_argument(
        "--yaml-path",
        type=Path,
        default=YAML_PATH,
        help="Path to special_events.yml",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        cal = fetch_ical(args.url)
    except Exception as e:  # noqa: BLE001 — we want to swallow any fetch error
        logger.warning("failed to fetch %s: %s — exiting cleanly", args.url, e)
        return 0

    existing = load_existing_yaml(args.yaml_path)
    date_to_names, source_uids = build_dedup_index(existing)
    logger.info(
        "loaded %d existing events (%d with source_uid)",
        len(existing),
        len(source_uids),
    )

    today = dt.date.today()
    lookahead = today + dt.timedelta(days=LOOKAHEAD_DAYS)

    candidates: list[dict] = []
    skipped_dedup = 0
    skipped_window = 0
    for component in cal.walk("VEVENT"):
        try:
            uid = str(component.get("UID", "")).strip()
            summary = str(component.get("SUMMARY", "")).strip()
            if not summary:
                continue
            dtstart = component.get("DTSTART")
            if dtstart is None:
                continue
            date, time = extract_date_time(dtstart)
            end_date = extract_end_date(dtstart, component.get("DTEND"))
            if date < today or date > lookahead:
                skipped_window += 1
                continue
            if uid and uid in source_uids:
                skipped_dedup += 1
                continue
            if matches_existing(summary, date, date_to_names):
                skipped_dedup += 1
                continue
            venue, address = parse_location(str(component.get("LOCATION", "")))
            description = clean_description(str(component.get("DESCRIPTION", "")))
            url = str(component.get("URL", "")).strip() or None
            categories = component.get("CATEGORIES")
            tags = map_tags(categories)

            event = {
                "date": date,
                "end_date": end_date,
                "name": summary,
                "venue": venue or "Angra do Heroísmo",
                "address": address,
                "map_url": build_map_url(venue or "Angra do Heroísmo"),
                "time": time,
                "description": description,
                "source_url": url,
                "source_uid": uid or None,
                "tags": tags,
            }
            candidates.append(event)
        except Exception as e:  # noqa: BLE001
            logger.warning("skipping malformed VEVENT: %s", e)
            continue

    logger.info(
        "found %d new candidate events (skipped %d dedup, %d out-of-window)",
        len(candidates),
        skipped_dedup,
        skipped_window,
    )

    if not candidates:
        logger.info("nothing to add.")
        return 0

    candidates.sort(key=lambda e: e["date"])

    if len(candidates) > args.max_events:
        logger.warning(
            "capping %d candidates to --max-events=%d",
            len(candidates),
            args.max_events,
        )
        candidates = candidates[: args.max_events]

    block = f"\n# Auto-ingested from CMAH ({today.isoformat()})\n"
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
