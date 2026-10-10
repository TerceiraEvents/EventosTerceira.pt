#!/usr/bin/env python3
"""Read every published What’s On agenda page through its public website data query."""
from __future__ import annotations

import copy
import datetime as dt
import json
import re
import sys

from ingest_common import clean_description, is_similar_match, normalize_name
from ingest_dates import published_dates, published_time
from ingest_health import SourceError, SourceHealth, run_ingester

PROJECT_ID = "s51ryo6rirdnhc5r"
REPEATER_ID = "c09Ov7jGKeOQKPn6"
STRUCT_URL = f"https://cdn.bndlyr.com/{PROJECT_ID}/_p/struct.js"
QUERY_URL = "https://repeater.bondlayer.com/fetch"
BASE_URL = "https://whatson.azores.gov.pt"
MAX_PAGES = 50
CATEGORY_TAGS = {
    "cinema": "cinema", "musica": "live-music", "teatro": "theater",
    "danca": "dance", "desporto": "outdoor",
    "exposicao": "exhibition", "fotografia": "exhibition",
    "artes visuais": "exhibition", "literatura": "literature",
    "poesia": "literature", "oficinas e masterclasses": "workshop",
    "gastronomia": "food-drink", "conferencias e seminarios": "literature",
}


def localized(value) -> str:
    """Choose the published Portuguese value without translating venue names."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("pt") or value.get("all") or "").strip()
    return ""


def _structure(payload: bytes) -> dict:
    text = payload.decode("utf-8")
    match = re.fullmatch(r"\s*window\.BndLyrStruct\s*=\s*(\{.*\})\s*;?\s*", text, re.S)
    if not match:
        raise SourceError("What’s On: unrecognized published site structure")
    try:
        structure = json.loads(match[1])
        repeater = structure["repeaters"][REPEATER_ID]
        if not repeater.get("pagination", {}).get("enabled"):
            raise SourceError("What’s On: agenda pagination schema changed")
        return structure
    except (ValueError, KeyError, TypeError) as exc:
        raise SourceError(f"What’s On: invalid published structure: {exc}") from exc


def fetch_records(health: SourceHealth) -> tuple[list[dict], dict]:
    """Fetch all agenda pages with loop, cap, and response-schema checks."""
    structure = _structure(health.fetch(STRUCT_URL))
    repeater = copy.deepcopy(structure["repeaters"][REPEATER_ID])
    items, related, seen = [], {}, set()
    expected_pages = None
    for page in range(1, MAX_PAGES + 1):
        repeater["page"] = page
        request = {
            "hash": str(structure["hash"]), "locale": "pt", "target": "production",
            "geoData": {"lat": 0, "lon": 0}, "searchQuery": "",
            "repeater": repeater, "projectId": PROJECT_ID, "contentId": "0", "favorites": {},
        }
        try:
            response = json.loads(health.fetch(QUERY_URL, request))
        except ValueError as exc:
            raise SourceError("What’s On: data query did not return JSON") from exc
        if not isinstance(response, dict) or not isinstance(response.get("items"), list):
            raise SourceError("What’s On: invalid agenda response")
        total_pages = response.get("totalPages")
        if not isinstance(total_pages, int) or total_pages < 0 or total_pages > MAX_PAGES:
            raise SourceError("What’s On: missing or excessive page count")
        if response.get("page") != page or (expected_pages is not None and total_pages != expected_pages):
            raise SourceError("What’s On: pagination changed during discovery; retry the complete scan")
        expected_pages = total_pages
        batch = response["items"]
        if not batch and total_pages > 0:
            raise SourceError(f"What’s On: advertised page {page} is empty")
        for item in batch:
            if not isinstance(item, dict) or not item.get("id") or item["id"] in seen:
                raise SourceError("What’s On: invalid or repeated record across pages")
            seen.add(item["id"])
            items.append(item)
        if not isinstance(response.get("related", {}), dict):
            raise SourceError("What’s On: invalid island/category references")
        related.update(response.get("related", {}))
        if page >= total_pages:
            health.listed += len(items)
            return items, related
    raise SourceError("What’s On: pagination cap reached before completion")


def parse_record(item: dict, related: dict, known_events: list[dict] | None = None) -> list[dict]:
    """Parse actual displayed session dates; CMS publication timestamps are not starts."""
    title = clean_description(localized(item.get("_title")))
    slug = localized(item.get("_slug"))
    venue = clean_description(localized(item.get("text_venue")))
    label = localized(item.get("text_display_date"))
    description = clean_description(re.sub(r"</?(?:p|div|br|li)\b[^>]*>", " ",
                                          localized(item.get("text_description"))), max_chars=12000)
    if not title or not slug or not venue:
        raise SourceError(f"What’s On: incomplete title, slug, or venue for {item.get('id')}")
    try:
        metadata_end = dt.datetime.fromisoformat(str(item["datetime_end_date"]).replace("Z", "+00:00")).date()
        year = metadata_end.year
        if normalize_name(label).startswith("ate "):
            end = published_dates(re.sub(r"^\s*Até\s+", "", label, flags=re.I), year)[0][1]
            known = next((event for event in (known_events or [])
                          if isinstance(event.get("date"), dt.date)
                          and event["date"] <= end
                          and is_similar_match(title, event.get("name", ""))), None)
            if known is None:
                raise ValueError("end-only exhibition has no previously verified start date")
            dates = [(known["date"], end)]
        else:
            dates = published_dates(label, year)
        if not re.search(r"\b20\d{2}\b", label) and abs((dates[-1][1] - metadata_end).days) > 60:
            raise ValueError("displayed date and CMS end date disagree; the event year needs review")
    except (KeyError, ValueError, TypeError) as exc:
        raise SourceError(f"What’s On: {title}: {exc}") from exc
    category_id = item.get("ref_category")
    if category_id is not None and not isinstance(category_id, str):
        raise SourceError(f"What’s On: invalid category reference for {title}")
    category = normalize_name(localized(related.get(category_id, {}).get("_title")))
    tags = [CATEGORY_TAGS[category]] if category in CATEGORY_TAGS else []
    if re.search(r"entrada (?:livre|gratuita)|acesso livre", normalize_name(description)):
        tags.append("free")
    time = published_time(label) or published_time(localized(item.get("text_description")))
    events = []
    for start, end in dates:
        event = {
            "date": start, "name": title, "venue": venue, "time": time,
            "description": clean_description(description),
            "source_url": f"{BASE_URL}/evento/{slug}/",
            "source_uid": f"{item['id']}:{start.isoformat()}@whatson.azores.gov.pt",
            "tags": tags,
        }
        if end > start:
            event["end_date"] = end
        events.append(event)
    return events


def discover_events(today: dt.date, lookahead: dt.date, health: SourceHealth) -> list[dict]:
    """Select records by their explicit island reference and report ambiguous dates."""
    records, related = fetch_records(health)
    if not records:
        return []
    if any(not isinstance(value, dict) for value in related.values()):
        raise SourceError("What’s On: reference metadata is not an object")
    island_ids = {key for key, value in related.items()
                  if normalize_name(localized(value.get("_title"))) == "terceira"}
    if not island_ids:
        raise SourceError("What’s On: no Terceira island reference in agenda metadata")
    events, errors = [], []
    for item in records:
        if not isinstance(item.get("ref_local"), str) or item["ref_local"] not in related:
            raise SourceError(f"What’s On: missing or unknown island reference for {item.get('id')}")
        if item.get("ref_local") not in island_ids:
            continue
        health.local += 1
        label = normalize_name(localized(item.get("text_display_date")))
        title = normalize_name(localized(item.get("_title")))
        if re.match(r"(?:a partir|todas|todos)\b", label) or (
            "temporada" in title and "domingos" in normalize_name(localized(item.get("text_description")))
        ):
            health.rejected += 1
            health.warnings.append(f"Recurring programme requires weekly-data review: {localized(item.get('_title'))}")
            continue
        try:
            parsed = parse_record(item, related, health.known_events)
            events.extend(parsed)
            health.parsed += len(parsed)
        except SourceError as exc:
            health.rejected += 1
            errors.append(str(exc))
    if errors:
        raise SourceError("; ".join(errors))
    return events


def main() -> int:
    return run_ingester("What's On Azores", discover_events)


if __name__ == "__main__":
    sys.exit(main())
