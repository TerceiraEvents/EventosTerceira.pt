#!/usr/bin/env python3
"""Ingest Terceira events from Visit Azores (visitazores.com).

Source: https://www.visitazores.com/en/events

Regional tourism board event listings. We pull the events listing page,
extract JSON-LD `Event` blocks, and filter to Terceira-relevant items.

If the page stops embedding JSON-LD, this script will start no-opping;
we'll switch to a different parsing strategy without breaking the cron.

See ingest_common.py + ingest_jsonld.py for the shared helpers.
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from pathlib import Path

from ingest_common import (
    DEFAULT_MAX_EVENTS,
    LOOKAHEAD_DAYS,
    YAML_PATH,
    build_dedup_index,
    format_event_yaml,
    load_existing_yaml,
    matches_existing,
)
from ingest_jsonld import JsonLdSource, harvest

SOURCE = JsonLdSource(
    slug="visitazores.com",
    listing_url="https://www.visitazores.com/en/events",
    region_keyword="terceira",
    default_locality="Angra do Heroísmo",
)

logger = logging.getLogger("ingest_visit_azores")


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

    raw_events = harvest(SOURCE)
    logger.info(
        "harvested %d JSON-LD Terceira events from %s",
        len(raw_events), SOURCE.listing_url,
    )
    if not raw_events:
        return 0

    existing = load_existing_yaml(args.yaml_path)
    date_to_names, source_uids = build_dedup_index(existing)
    today = dt.date.today()
    lookahead = today + dt.timedelta(days=LOOKAHEAD_DAYS)

    candidates: list[dict] = []
    skipped_dedup = 0
    skipped_window = 0
    for event in raw_events:
        if event["date"] < today or event["date"] > lookahead:
            skipped_window += 1
            continue
        if event["source_uid"] and event["source_uid"] in source_uids:
            skipped_dedup += 1
            continue
        if matches_existing(event["name"], event["date"], date_to_names):
            skipped_dedup += 1
            continue
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

    block = f"\n# Auto-ingested from Visit Azores ({today.isoformat()})\n"
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
