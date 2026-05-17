#!/usr/bin/env python3
"""Ingest events from the Câmara Municipal da Praia da Vitória into _data/special_events.yml.

Source: https://www.cmpv.pt/

CMPV publishes municipal events through their main site. We try, in order:

  1. The expected iCal endpoint (`/events.ics`) — same convention CMAH uses.
  2. A few common WordPress / generic patterns (`/eventos/feed/`,
     `/events/?ical=1`, `/feed/`) — these municipal sites typically run on
     CMS templates that ship one or more of these.

If none of them return parseable events, the script exits cleanly. This is
the same defensive shape as ingest_museu_angra.py — wrong-endpoint runs
no-op, so the daily cron doesn't email anyone or push junk PRs.

Praia da Vitória is the *other* municipality on Terceira; CMAH's iCal feed
doesn't cover any of it. This is the gap this script fills.

See ingest_common.py for the shared dedup / format helpers.
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
)

BASE_URL = "https://www.cmpv.pt"

# Tried in order. First one that parses any VEVENTs wins.
CANDIDATE_ICAL_URLS = [
    f"{BASE_URL}/events.ics",
    f"{BASE_URL}/eventos.ics",
    f"{BASE_URL}/events/?ical=1",
    f"{BASE_URL}/eventos/?ical=1",
    f"{BASE_URL}/?ical=1",
    f"{BASE_URL}/eventos/feed/",
    f"{BASE_URL}/feed/",
]

DEFAULT_LOCALITY = "Praia da Vitória"

# Praia hosts a lot of municipal cinema / concerts / sports. Same conservative
# category-to-tag mapping shape as ingest_cmah.py, in case CMPV's feed uses
# CATEGORIES on its VEVENTs.
CATEGORY_TAG_MAP = {
    "Cinema": "cinema",
    "Exposição": "exhibition",
    "Exposições": "exhibition",
    "Música": "live-music",
    "Concerto": "live-music",
    "Concertos": "live-music",
    "Teatro": "theater",
    "Dança": "dance",
    "Literatura": "literature",
    "Livros": "literature",
    "Workshop": "workshop",
    "Oficina": "workshop",
    "Família": "kid-friendly",
    "Infantil": "kid-friendly",
    "Tourada": "bullfighting",
    "Touradas": "bullfighting",
    "Gastronomia": "food-drink",
    "Ar livre": "outdoor",
}

logger = logging.getLogger("ingest_cmpv")


def _fetch(url: str, timeout: int = 30) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:  # noqa: BLE001
        logger.debug("%s → %s", url, e)
        return None


def _parse_ical(payload: bytes) -> list:
    try:
        return list(icalendar.Calendar.from_ical(payload).walk("VEVENT"))
    except Exception as e:  # noqa: BLE001
        logger.debug("not iCal: %s", e)
        return []


def discover_vevents() -> list:
    """Walk the candidate URL list and return the first non-empty VEVENT list."""
    for url in CANDIDATE_ICAL_URLS:
        payload = _fetch(url)
        if not payload:
            continue
        events = _parse_ical(payload)
        if events:
            logger.info("source endpoint: %s (%d VEVENTs)", url, len(events))
            return events
    return []


def _extract_date_time(prop) -> tuple[dt.date, str | None]:
    value = prop.dt
    value_param = prop.params.get("VALUE") if hasattr(prop, "params") else None
    if value_param == "DATE":
        if isinstance(value, dt.datetime):
            return (value.date(), None)
        return (value, None)
    if isinstance(value, dt.datetime):
        hhmm = value.strftime("%H:%M")
        return (value.date(), None if hhmm == "00:00" else hhmm)
    if isinstance(value, dt.date):
        return (value, None)
    raise ValueError(f"unexpected DTSTART type: {type(value).__name__}")


def _split_location(loc: str) -> tuple[str, str]:
    if not loc:
        return ("", "")
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    if not parts:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    drop = {"Portugal", "Região Autónoma dos Açores", "Ilha Terceira"}
    return (parts[0], ", ".join(p for p in parts[1:] if p not in drop))


def _map_tags(categories) -> list[str]:
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

    vevents = discover_vevents()
    if not vevents:
        logger.info("no iCal endpoint returned events for CMPV — exiting cleanly")
        return 0

    existing = load_existing_yaml(args.yaml_path)
    date_to_names, source_uids = build_dedup_index(existing)
    logger.info(
        "loaded %d existing events (%d with source_uid)",
        len(existing), len(source_uids),
    )

    today = dt.date.today()
    lookahead = today + dt.timedelta(days=LOOKAHEAD_DAYS)

    candidates: list[dict] = []
    skipped_dedup = 0
    skipped_window = 0
    for component in vevents:
        try:
            uid = str(component.get("UID", "")).strip()
            summary = str(component.get("SUMMARY", "")).strip()
            if not summary:
                continue
            dtstart = component.get("DTSTART")
            if dtstart is None:
                continue
            date, time = _extract_date_time(dtstart)
            if date < today or date > lookahead:
                skipped_window += 1
                continue
            if uid and uid in source_uids:
                skipped_dedup += 1
                continue
            if matches_existing(summary, date, date_to_names):
                skipped_dedup += 1
                continue
            venue, address = _split_location(str(component.get("LOCATION", "")))
            description = clean_description(str(component.get("DESCRIPTION", "")))
            url = str(component.get("URL", "")).strip() or None
            tags = _map_tags(component.get("CATEGORIES"))

            candidates.append(
                {
                    "date": date,
                    "name": summary,
                    "venue": venue or DEFAULT_LOCALITY,
                    "address": address,
                    "map_url": build_map_url(venue or DEFAULT_LOCALITY, DEFAULT_LOCALITY),
                    "time": time,
                    "description": description,
                    "source_url": url,
                    "source_uid": uid or None,
                    "tags": tags,
                }
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("skipping malformed VEVENT: %s", e)
            continue

    logger.info(
        "found %d new candidate events (skipped %d dedup, %d out-of-window)",
        len(candidates), skipped_dedup, skipped_window,
    )

    if not candidates:
        logger.info("nothing to add.")
        return 0

    candidates.sort(key=lambda e: e["date"])
    if len(candidates) > args.max_events:
        logger.warning(
            "capping %d candidates to --max-events=%d",
            len(candidates), args.max_events,
        )
        candidates = candidates[: args.max_events]

    block = f"\n# Auto-ingested from CMPV ({today.isoformat()})\n"
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
