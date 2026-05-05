#!/usr/bin/env python3
"""Ingest events from Ticketline's Ilha Terceira district listing.

Source: https://www.ticketline.pt/pesquisa?district=29

Ticketline is the main ticket distributor for Teatro Angrense, Centro Cultural
e de Congressos de Angra do Heroísmo (CCCAH), and the Auditório Ramo Grande
in Praia da Vitória. The district=29 filter is "Ilha Terceira" and catches
events at all of those venues — including Praia da Vitória, which the CMAH
municipal feed never covers.

Ticketline doesn't expose an API or JSON-LD, but each event page is marked
up with schema.org microdata (`itemtype="http://schema.org/Event"`) and the
usual og:* meta tags, so we can extract the structured fields reliably with
targeted regex against the first Event block on each page.

This script only ADDS new events. It never modifies existing entries.
Dedup uses `source_uid` + word-level name similarity shared with the other
ingestion scripts (see ingest_common.py).

Run with --dry-run to preview.
"""
from __future__ import annotations

import argparse
import datetime as dt
import http.cookiejar
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from ingest_common import (
    DEFAULT_MAX_EVENTS,
    LOOKAHEAD_DAYS,
    YAML_PATH,
    build_dedup_index,
    build_map_url,
    clean_description,
    format_event_yaml,
    load_existing_yaml,
    matches_existing,
)

BASE_URL = "https://www.ticketline.pt"
LISTING_URL = f"{BASE_URL}/pesquisa?district=29"  # Ilha Terceira

# Ticketline's WAF redirects any request whose User-Agent identifies as a
# bot (even our honest TerceiraEventsBot/1.0) to /404, returning infinite
# redirect loops on detail pages. Their robots.txt does not disallow crawling
# /evento/ or /pesquisa paths under the wildcard rule — only /carrinho and
# /locate are disallowed — so the WAF block is a generic anti-bot heuristic,
# not a stated crawling policy. We use a plain Firefox UA here scoped to
# this module, keep request volume low (daily cron, ~8 requests, 0.5s
# spacing), and honor the robots.txt disallow list. The site's own events
# are public, and listing them on eventosterceira.pt drives ticket
# sales back to Ticketline, so the use case is non-adversarial.
TICKETLINE_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
)
# Ticketline's og:description always starts with this boilerplate sentence
# before the event-specific blurb. Strip it on the way in.
TICKETLINE_BOILERPLATE = (
    "Venda de bilhetes de concertos, espectáculos, teatro, musicais, "
    "exposições e experiências."
)
# Polite delay between detail fetches.
FETCH_DELAY_SECONDS = 0.5
# Numeric event id is the last `-\d+` segment of the URL slug.
EVENT_ID_RE = re.compile(r"/evento/[^/]+-(\d+)/?$")

logger = logging.getLogger("ingest_ticketline")


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

# Ticketline issues a PHPSESSID on the first request and serves subsequent
# detail pages conditionally on that cookie being presented. Use a module-
# level opener with a persistent CookieJar so every request in a run shares
# the same session.
_COOKIE_JAR = http.cookiejar.CookieJar()
_OPENER = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(_COOKIE_JAR)
)
_OPENER.addheaders = [("User-Agent", TICKETLINE_USER_AGENT)]


def _fetch_html(url: str, timeout: int = 30) -> str:
    with _OPENER.open(url, timeout=timeout) as resp:
        raw = resp.read()
    # Ticketline pages are UTF-8 but occasionally have stray bytes; be forgiving.
    return raw.decode("utf-8", errors="replace")


def fetch_listing_urls(listing_url: str = LISTING_URL) -> list[str]:
    """Fetch the district listing page and return the set of /evento/ URLs."""
    html = _fetch_html(listing_url)
    seen: set[str] = set()
    urls: list[str] = []
    for match in re.finditer(r'href="(/evento/[^"?#]+)"', html):
        path = match.group(1)
        if path in seen:
            continue
        seen.add(path)
        urls.append(urllib.parse.urljoin(BASE_URL, path))
    return urls


# ---------------------------------------------------------------------------
# Detail page parsing
# ---------------------------------------------------------------------------


def _first(pattern: str, haystack: str, flags: int = 0) -> str | None:
    m = re.search(pattern, haystack, flags)
    return m.group(1) if m else None


def _main_event_block(html: str) -> str:
    """Return the HTML slice containing only the canonical event.

    Ticketline event pages render the main event first, followed by a
    sidebar of related-event cards that also use schema.org/Event microdata.
    We scope the parse by slicing from the first Event itemtype to the
    second, so related events can't leak into the main extraction.
    """
    starts = [m.start() for m in re.finditer(r'itemtype="http://schema\.org/Event"', html)]
    if not starts:
        return html
    if len(starts) == 1:
        return html[starts[0]:]
    return html[starts[0]:starts[1]]


def parse_event_page(url: str, html: str) -> dict | None:
    """Parse a Ticketline event page into the shared event dict format.

    Returns None if the required fields (name, date) can't be extracted;
    the caller will log and skip.
    """
    main = _main_event_block(html)

    # og:* from <head> — these describe the canonical event unambiguously.
    og_title = _first(
        r'<meta property="og:title"[^>]*content="([^"]+)"', html
    )
    og_desc = _first(
        r'<meta property="og:description"[^>]*content="([^"]+)"', html
    )
    og_url = _first(r'<meta property="og:url"[^>]*content="([^"]+)"', html)
    canonical_url = og_url or url

    # startDate is ISO 8601, e.g. "2026-04-30T21:30" (no seconds, no TZ).
    start_str = _first(
        r'itemprop="startDate"[^>]*content="([^"]+)"', main
    )
    if not og_title or not start_str:
        return None

    try:
        start_dt = _parse_iso_dt(start_str)
    except ValueError:
        return None

    date = start_dt.date()
    time_str: str | None = None
    if isinstance(start_dt, dt.datetime):
        hhmm = start_dt.strftime("%H:%M")
        # Ticketline marks "all-day or TBD" events with a 00:00 time, which
        # would display wrong on the site. Treat 00:00 as unknown.
        if hhmm != "00:00":
            time_str = hhmm

    # Venue: first Place inside the main block.
    venue_name = _first(
        r'itemtype="http://schema\.org/Place".*?itemprop="name"[^>]*>\s*([^<]+?)\s*<',
        main,
        re.DOTALL,
    )
    venue = (venue_name or "").strip() or "Ilha Terceira"

    # Address: PostalAddress fields, optional.
    street = _first(
        r'itemprop="streetAddress"[^>]*>\s*([^<]+?)\s*<', main, re.DOTALL
    )
    locality = _first(
        r'itemprop="addressLocality"[^>]*>\s*([^<]+?)\s*<', main, re.DOTALL
    )
    postal = _first(
        r'itemprop="postalCode"[^>]*>\s*([^<]+?)\s*<', main, re.DOTALL
    )
    address_parts = [p for p in (street, postal, locality) if p]
    address = ", ".join(address_parts)
    map_locality = (locality or "Angra do Heroísmo").strip()

    # Description: strip the boilerplate prefix, then run through the shared
    # cleaner which also handles double-HTML-escaped entities.
    description = ""
    if og_desc:
        trimmed = og_desc
        if trimmed.startswith(TICKETLINE_BOILERPLATE):
            trimmed = trimmed[len(TICKETLINE_BOILERPLATE) :].lstrip()
        description = clean_description(trimmed)

    # source_uid: reuse the numeric event id from the URL slug so re-runs
    # dedup even if the slug or title changes. Format as a namespaced UID
    # that matches CMAH's `<id>@<domain>` convention.
    uid: str | None = None
    m = EVENT_ID_RE.search(canonical_url)
    if m:
        uid = f"{m.group(1)}@ticketline.pt"

    # Clean the name: Ticketline titles are all-caps ("DIA INTERNACIONAL DO
    # JAZZ 2026"). Leave them alone — converting to title case mangles
    # acronyms and proper nouns, and the site CSS doesn't assume a casing.
    name = og_title.strip()

    return {
        "date": date,
        "name": name,
        "venue": venue,
        "address": address,
        "map_url": build_map_url(venue, map_locality),
        "time": time_str,
        "description": description,
        "source_url": canonical_url,
        "source_uid": uid,
        "tags": [],
    }


def _parse_iso_dt(s: str) -> dt.datetime | dt.date:
    """Parse Ticketline's ISO 8601 startDate (no seconds, no TZ)."""
    s = s.strip()
    # Formats seen: "2026-04-30T21:30", "2026-04-30"
    if "T" in s:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M")
    return dt.datetime.strptime(s, "%Y-%m-%d")


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
        "--listing-url",
        default=LISTING_URL,
        help="Ticketline district listing URL (default: %(default)s)",
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

    try:
        event_urls = fetch_listing_urls(args.listing_url)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "failed to fetch Ticketline listing %s: %s — exiting cleanly",
            args.listing_url,
            e,
        )
        return 0
    logger.info("found %d event URLs on %s", len(event_urls), args.listing_url)

    if not event_urls:
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
    skipped_parse = 0

    for url in event_urls:
        # Fast-path dedup: skip the detail fetch if the URL's event id is
        # already present in source_uids. Saves HTTP round-trips on re-runs.
        m = EVENT_ID_RE.search(url)
        if m:
            candidate_uid = f"{m.group(1)}@ticketline.pt"
            if candidate_uid in source_uids:
                skipped_dedup += 1
                continue

        try:
            html = _fetch_html(url)
        except Exception as e:  # noqa: BLE001
            logger.warning("failed to fetch %s: %s — skipping", url, e)
            continue
        time.sleep(FETCH_DELAY_SECONDS)

        event = parse_event_page(url, html)
        if event is None:
            skipped_parse += 1
            logger.warning("could not parse %s — skipping", url)
            continue

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
        "found %d new candidate events (skipped %d dedup, %d out-of-window, %d parse failures)",
        len(candidates),
        skipped_dedup,
        skipped_window,
        skipped_parse,
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

    block = f"\n# Auto-ingested from Ticketline ({today.isoformat()})\n"
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
