"""Shared JSON-LD Event extraction for ingest scripts.

A growing number of modern tourism sites (Azores What's On, Visit Azores,
the new museum portals) publish schema.org Event blocks as JSON-LD inside
their listing and detail pages for SEO. When that's true we can ingest from
them without writing a bespoke HTML parser per site — extract the JSON-LD,
filter by name/region, and feed it through the shared dedup machinery.

This module is the common bit. Per-site wrappers (`ingest_whatson_azores.py`,
`ingest_visit_azores.py`) just provide:
  - the listing URL,
  - a region/keyword filter (so we don't ingest São Miguel events into a
    Terceira-only calendar),
  - a default locality string for `build_map_url`,
  - a source slug used to build `source_uid`s.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable

from ingest_common import USER_AGENT, build_map_url, clean_description

logger = logging.getLogger("ingest_jsonld")

# `<script type="application/ld+json">…</script>` (forgiving on whitespace
# and on the presence of additional attributes).
JSONLD_BLOCK_RE = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)


@dataclass(frozen=True)
class JsonLdSource:
    """Configuration for a JSON-LD-based ingest source."""

    slug: str  # used as the @-suffix on source_uid (e.g. "whatson.azores.gov.pt")
    listing_url: str
    # Substring (case-insensitive) that must appear in either the event name,
    # description, or location for the event to be ingested. Used to filter
    # multi-island feeds down to Terceira.
    region_keyword: str = "terceira"
    default_locality: str = "Angra do Heroísmo"
    # Hard cap on detail-page fetches per run to keep the cron polite.
    max_detail_fetches: int = 30


def fetch(url: str, timeout: int = 30) -> str | None:
    """GET `url` and return text on 2xx, None on any failure (logged)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except Exception as e:  # noqa: BLE001
        logger.warning("fetch failed for %s: %s", url, e)
        return None
    return raw.decode("utf-8", errors="replace")


def _iter_jsonld_objects(html: str) -> Iterable[dict]:
    """Yield every JSON object parsed from the page's JSON-LD <script> blocks.

    JSON-LD blocks can hold either a single object, a list, or a `@graph`
    wrapping a list — we flatten all three shapes into a stream of dicts.
    """
    for match in JSONLD_BLOCK_RE.finditer(html):
        raw = match.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            objs = data
        elif isinstance(data, dict) and isinstance(data.get("@graph"), list):
            objs = data["@graph"]
        elif isinstance(data, dict):
            objs = [data]
        else:
            continue
        for obj in objs:
            if isinstance(obj, dict):
                yield obj


def _is_event(obj: dict) -> bool:
    t = obj.get("@type")
    if isinstance(t, str):
        return t == "Event" or t.endswith("Event")
    if isinstance(t, list):
        return any(isinstance(s, str) and (s == "Event" or s.endswith("Event")) for s in t)
    return False


def _extract_location(loc: object, default_name: str, default_address: str) -> tuple[str, str]:
    """Return (venue_name, address) from a JSON-LD `location` payload."""
    if isinstance(loc, str):
        return (loc.strip() or default_name, default_address)
    if not isinstance(loc, dict):
        return (default_name, default_address)
    name = (loc.get("name") or "").strip() or default_name
    addr = loc.get("address")
    if isinstance(addr, str):
        address = addr.strip()
    elif isinstance(addr, dict):
        parts = [
            (addr.get("streetAddress") or "").strip(),
            (addr.get("postalCode") or "").strip(),
            (addr.get("addressLocality") or "").strip(),
        ]
        address = ", ".join(p for p in parts if p)
    else:
        address = ""
    return (name, address or default_address)


def _parse_start(start: object) -> tuple[dt.date, str | None] | None:
    if not isinstance(start, str) or not start:
        return None
    text = start.strip()
    # Try the common shapes: full ISO with TZ, ISO without TZ, date-only.
    candidates = [text]
    # Strip trailing "Z" / "+00:00" so fromisoformat handles older Python.
    if text.endswith("Z"):
        candidates.append(text[:-1])
    try:
        for c in candidates:
            try:
                obj = dt.datetime.fromisoformat(c)
                hhmm = obj.strftime("%H:%M")
                return (obj.date(), None if hhmm == "00:00" else hhmm)
            except ValueError:
                continue
        return (dt.date.fromisoformat(text[:10]), None)
    except ValueError:
        return None


def _matches_region(obj: dict, parsed: dict, keyword: str) -> bool:
    """Loose region filter — keyword present in name, description, or location."""
    if not keyword:
        return True
    keyword = keyword.lower()
    bucket = " ".join(
        [
            (obj.get("name") or "")[:200],
            (obj.get("description") or "")[:500],
            parsed.get("venue") or "",
            parsed.get("address") or "",
        ]
    ).lower()
    return keyword in bucket


def harvest(source: JsonLdSource) -> list[dict]:
    """Fetch the listing URL and return JSON-LD Event objects as event dicts.

    Detail pages are not fetched: most JSON-LD-rich sites embed enough on
    the listing page itself to build a complete entry. If they don't, the
    caller can extend this with a detail fetch loop, but every extra
    round-trip hits the source so we keep the default minimal.
    """
    html = fetch(source.listing_url)
    if not html:
        return []

    events: list[dict] = []
    seen_ids: set[str] = set()
    for obj in _iter_jsonld_objects(html):
        if not _is_event(obj):
            continue
        name = (obj.get("name") or "").strip()
        start = _parse_start(obj.get("startDate"))
        if not name or not start:
            continue
        date, time_str = start

        venue, address = _extract_location(
            obj.get("location"),
            default_name=source.default_locality,
            default_address="",
        )
        description = clean_description(obj.get("description") or "")
        url = (obj.get("url") or "").strip() or None

        # Build a stable UID: prefer the @id property, fall back to the URL,
        # else the (name, start) tuple. Skip duplicates within a single run.
        uid_raw = obj.get("@id") or url or f"{name}|{obj.get('startDate', '')}"
        uid = f"{uid_raw}@{source.slug}"
        if uid in seen_ids:
            continue
        seen_ids.add(uid)

        parsed = {
            "date": date,
            "name": name,
            "venue": venue,
            "address": address,
            "map_url": build_map_url(venue, source.default_locality),
            "time": time_str,
            "description": description,
            "source_url": url,
            "source_uid": uid,
            "tags": [],
        }
        if not _matches_region(obj, parsed, source.region_keyword):
            continue
        events.append(parsed)

    return events
