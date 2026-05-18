#!/usr/bin/env python3
"""Ingest events from the Museu de Angra do Heroísmo into _data/special_events.yml.

Source: https://museu-angra.cultura.azores.gov.pt/

The museum runs WordPress with The Events Calendar plugin. We try, in order:

  1. The REST API (`/wp-json/tribe/events/v1/events`) — cleanest, returns JSON.
  2. The plugin's iCal endpoint (`/events/?ical=1`) — same data as RSS but
     with timezone-aware datetimes.
  3. The plugin's RSS feed (`/events/feed/`) — same items as the listing but
     stripped of structured fields.

If all three return nothing usable, the script exits cleanly (rc=0). We do
NOT HTML-scrape `/agenda/` because the museum's calendar layout is
JavaScript-driven and the static HTML doesn't carry the date/time info we'd
need. If the REST/iCal endpoints disappear, the script will start no-opping
and we'll switch to a JS-rendered scrape in a follow-up.

This script only ADDS new events. It never modifies existing entries.
Dedup uses `source_uid` + word-level name similarity shared with the other
ingestion scripts (see ingest_common.py).

Run with --dry-run to preview without modifying the file.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
import urllib.parse
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

BASE_URL = "https://museu-angra.cultura.azores.gov.pt"
REST_URL = f"{BASE_URL}/wp-json/tribe/events/v1/events"
ICAL_URL = f"{BASE_URL}/events/?ical=1"

# Museum's display address — used as the default when an event omits venue
# details. Lifted from _data/venues.yml so the two stay in sync.
DEFAULT_VENUE = "Museu de Angra do Heroísmo"
DEFAULT_ADDRESS = "Ladeira de São Francisco, 9700-182 Angra do Heroísmo"

# Hosted at the museum, always categorise as exhibition + free unless the
# specific event description shouts otherwise. Programming-style activities
# (Domingos com Música, talks, family workshops) get extra tags on top.
DEFAULT_TAGS = ["exhibition", "free"]

# Keyword → tag hints for the title/description. Conservative — anything not
# matched falls through with just DEFAULT_TAGS.
KEYWORD_TAG_HINTS = {
    "concerto": "live-music",
    "música": "live-music",
    "audição": "live-music",
    "recital": "live-music",
    "palestra": "literature",
    "conferência": "literature",
    "apresentação de livro": "literature",
    "clube de leitura": "literature",
    "família": "kid-friendly",
    "crianças": "kid-friendly",
    "oficina": "workshop",
    "workshop": "workshop",
    "exposição": "exhibition",
    "exhibition": "exhibition",
    "almoço": "food-drink",
    "jantar": "food-drink",
}

logger = logging.getLogger("ingest_museu_angra")


# ---------------------------------------------------------------------------
# Fetching helpers
# ---------------------------------------------------------------------------


def _fetch(url: str, timeout: int = 30) -> bytes | None:
    """GET `url`, returning bytes on 2xx, None on any failure.

    Failures are logged at WARNING and swallowed so the script can fall
    through to the next discovery method without crashing the workflow.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:  # noqa: BLE001
        logger.warning("fetch failed for %s: %s", url, e)
        return None


def _tags_for(name: str, description: str) -> list[str]:
    """Pick a small set of tags from title + description keywords."""
    haystack = f"{name}\n{description}".lower()
    tags = list(DEFAULT_TAGS)
    for keyword, slug in KEYWORD_TAG_HINTS.items():
        if keyword in haystack and slug not in tags:
            tags.append(slug)
    return tags


def _make_uid(event_id: object) -> str | None:
    if event_id in (None, ""):
        return None
    return f"{event_id}@museu-angra.cultura.azores.gov.pt"


# ---------------------------------------------------------------------------
# REST API parsing (preferred path)
# ---------------------------------------------------------------------------


def _parse_rest_api(payload: bytes) -> list[dict]:
    """Parse a Tribe Events REST response into shared event dicts.

    Schema: https://theeventscalendar.com/knowledgebase/rest-api/
    Returns whatever the API gave us, post-filtering to events the YAML can
    represent (i.e. with a parseable start_date).
    """
    try:
        body = json.loads(payload.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        logger.warning("REST JSON decode failed: %s", e)
        return []
    items = body.get("events") if isinstance(body, dict) else None
    if not isinstance(items, list):
        return []

    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        start_raw = item.get("start_date") or item.get("utc_start_date")
        if not title or not start_raw:
            continue
        try:
            # API returns "YYYY-MM-DD HH:MM:SS"; tolerate "T" separator too.
            start = dt.datetime.fromisoformat(str(start_raw).replace(" ", "T"))
        except ValueError:
            logger.debug("REST: unparseable start_date %r", start_raw)
            continue
        date = start.date()
        hhmm = start.strftime("%H:%M")
        time_str = None if hhmm == "00:00" else hhmm

        venue_obj = item.get("venue") if isinstance(item.get("venue"), dict) else {}
        venue = (venue_obj.get("venue") or "").strip() or DEFAULT_VENUE
        # Tribe's address is split across street / city / zip / country.
        addr_bits = [
            (venue_obj.get("address") or "").strip(),
            (venue_obj.get("zip") or "").strip(),
            (venue_obj.get("city") or "").strip(),
        ]
        address = ", ".join(b for b in addr_bits if b) or DEFAULT_ADDRESS

        description = clean_description(item.get("description") or item.get("excerpt") or "")
        url = (item.get("url") or "").strip() or None
        uid = _make_uid(item.get("id"))

        out.append(
            {
                "date": date,
                "name": title,
                "venue": venue,
                "address": address,
                "map_url": build_map_url(venue, "Angra do Heroísmo"),
                "time": time_str,
                "description": description,
                "source_url": url,
                "source_uid": uid,
                "tags": _tags_for(title, description),
            }
        )
    return out


# ---------------------------------------------------------------------------
# iCal fallback
# ---------------------------------------------------------------------------


def _parse_ical(payload: bytes) -> list[dict]:
    try:
        cal = icalendar.Calendar.from_ical(payload)
    except Exception as e:  # noqa: BLE001
        logger.warning("iCal parse failed: %s", e)
        return []

    out: list[dict] = []
    for component in cal.walk("VEVENT"):
        try:
            summary = str(component.get("SUMMARY", "")).strip()
            dtstart = component.get("DTSTART")
            if not summary or dtstart is None:
                continue
            value = dtstart.dt
            value_param = (
                dtstart.params.get("VALUE") if hasattr(dtstart, "params") else None
            )
            if isinstance(value, dt.datetime):
                date = value.date()
                hhmm = value.strftime("%H:%M")
                time_str = None if hhmm == "00:00" or value_param == "DATE" else hhmm
            elif isinstance(value, dt.date):
                date = value
                time_str = None
            else:
                continue

            uid_raw = str(component.get("UID", "")).strip()
            # iCal UIDs from The Events Calendar look like "12345@host.tld"
            # already — pass through unchanged when present, otherwise build
            # one from the URL if we have it.
            url = str(component.get("URL", "")).strip() or None
            if uid_raw:
                uid = uid_raw
            elif url:
                uid = url  # last-ditch
            else:
                uid = None

            location = str(component.get("LOCATION", "")).strip()
            venue, address = _split_ical_location(location)
            description = clean_description(str(component.get("DESCRIPTION", "")))

            out.append(
                {
                    "date": date,
                    "name": summary,
                    "venue": venue or DEFAULT_VENUE,
                    "address": address or DEFAULT_ADDRESS,
                    "map_url": build_map_url(venue or DEFAULT_VENUE, "Angra do Heroísmo"),
                    "time": time_str,
                    "description": description,
                    "source_url": url,
                    "source_uid": uid,
                    "tags": _tags_for(summary, description),
                }
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("skipping malformed VEVENT: %s", e)
            continue
    return out


def _split_ical_location(loc: str) -> tuple[str, str]:
    """The Events Calendar concatenates venue + address with ", ".

    We split on the first comma and treat the head as the venue, the tail
    as the address. Empty locations fall through to the museum defaults.
    """
    if not loc:
        return ("", "")
    if "," not in loc:
        return (loc.strip(), "")
    venue, rest = loc.split(",", 1)
    return (venue.strip(), rest.strip())


# ---------------------------------------------------------------------------
# Discovery: try REST first, fall back to iCal
# ---------------------------------------------------------------------------


def discover_events() -> list[dict]:
    """Try each known endpoint until one yields events."""
    rest_payload = _fetch(f"{REST_URL}?per_page=50&start_date=now")
    if rest_payload:
        events = _parse_rest_api(rest_payload)
        if events:
            logger.info("REST API returned %d events", len(events))
            return events
        logger.info("REST API returned 0 parseable events — trying iCal")

    ical_payload = _fetch(ICAL_URL)
    if ical_payload:
        events = _parse_ical(ical_payload)
        if events:
            logger.info("iCal returned %d events", len(events))
            return events
        logger.info("iCal returned 0 parseable events")

    return []


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

    raw_events = discover_events()
    if not raw_events:
        logger.info("no events discovered from museum — exiting cleanly")
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

    block = f"\n# Auto-ingested from Museu de Angra ({today.isoformat()})\n"
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
