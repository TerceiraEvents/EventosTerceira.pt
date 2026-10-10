#!/usr/bin/env python3
"""Read the museum's public event and exhibition archives and their detail pages."""
from __future__ import annotations

import datetime as dt
import re
import sys
import urllib.parse

from ingest_common import clean_description, normalize_name
from ingest_dates import published_dates, published_time
from ingest_health import SourceError, SourceHealth, run_ingester
from ingest_html import parse_html

BASE_URL = "https://museu-angra.cultura.azores.gov.pt"
ARCHIVES = (f"{BASE_URL}/events/", f"{BASE_URL}/exhibition/temporarias/", f"{BASE_URL}/exhibition/mostras/")
MAX_PAGES = 50
VENUES = {
    "aerogare civil das lajes": "Aerogare Civil das Lajes",
    "igreja de nossa senhora da guia": "Igreja de Nossa Senhora da Guia",
    "nucleo de historia militar": "Núcleo de História Militar Manuel Coelho Baptista de Lima",
    "carmina": "Carmina — Galeria de Arte Contemporânea Dimas Simas Lopes",
    "museu de angra do heroismo": "Museu de Angra do Heroísmo",
    "edificio de sao francisco": "Museu de Angra do Heroísmo",
}


def _tags_for(name: str, description: str) -> list[str]:
    text = normalize_name(name + " " + description)
    tags = []
    for keywords, tag in (
        (("musica", "concerto", "recital"), "live-music"),
        (("exposicao", "inauguracao"), "exhibition"),
        (("oficina", "workshop"), "workshop"),
        (("criancas", "familias"), "kid-friendly"),
        (("livro", "conferencia", "palestra"), "literature"),
    ):
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    if re.search(r"acesso livre|entrada (?:livre|gratuita)", text):
        tags.append("free")
    return tags


def parse_archive(payload: bytes, archive_url: str) -> tuple[list[dict], list[str]]:
    """Read dated archive cards and only pagination links published by the museum."""
    root = parse_html(payload)
    headings = [node for node in root.walk() if node.tag == "h1"]
    if not headings or not any("event" in normalize_name(node.text()) or "expos" in normalize_name(node.text()) for node in headings):
        raise SourceError(f"{archive_url}: response is not a museum archive")
    records = []
    cards = [node for node in root.walk() if node.has_class("card")]
    if not cards and not re.search(r"nenhum|sem eventos|sem exposicoes|nao foram encontrados", normalize_name(root.text())):
        raise SourceError(f"{archive_url}: missing archive cards and empty-state marker")
    for card in cards:
        title = next((node for node in card.walk() if node.has_class("card-title")), None)
        if title is None:
            raise SourceError(f"{archive_url}: card title schema changed")
        links = [node.attrs.get("href", "") for node in title.walk() if node.tag == "a"]
        dates = [node for node in card.walk() if node.tag == "p" and node.has_class("small")]
        if not dates:
            raise SourceError(f"{archive_url}: card date schema changed for {title.text()}")
        label = clean_description(dates[0].text())
        if not label:
            raise SourceError(f"{archive_url}: dated collection has an empty date for {title.text()}")
        try:
            sessions = published_dates(label, 0)
        except ValueError as exc:
            raise SourceError(f"{archive_url}: invalid date for {title.text()}: {exc}") from exc
        if not links:
            raise SourceError(f"{archive_url}: dated card has no detail link")
        url = urllib.parse.urljoin(archive_url, links[0])
        if urllib.parse.urlparse(url).netloc != urllib.parse.urlparse(BASE_URL).netloc:
            raise SourceError(f"{archive_url}: event link leaves the museum source")
        for start, end in sessions:
            records.append({"name": clean_description(title.text()), "date": start, "end_date": end, "source_url": url})
            if "/exhibitions/" in url:
                records[-1]["tags"] = ["exhibition"]
    pages = []
    for node in root.walk():
        if node.tag == "a" and (node.has_class("page-numbers") or "next" in (node.attrs.get("rel") or "").split()):
            url = urllib.parse.urljoin(archive_url, node.attrs.get("href", ""))
            if urllib.parse.urlparse(url).netloc != urllib.parse.urlparse(BASE_URL).netloc:
                raise SourceError(f"{archive_url}: invalid pagination link")
            if url not in pages:
                pages.append(url)
    return records, pages


def parse_detail(payload: bytes, record: dict) -> list[dict]:
    """Read published venue, admission, and discrete workshop/concert sessions."""
    root = parse_html(payload)
    content = next((node for node in root.walk() if node.has_class("post-content")), None)
    if content is None:
        raise SourceError(f"{record['source_url']}: missing event content")
    paragraphs = [clean_description(node.text(), max_chars=12000)
                  for node in content.walk() if node.tag == "p"]
    description = " ".join(paragraphs)
    text = normalize_name(description)
    if "apenas para quem participou" in text:
        return []
    location = next((normalize_name(paragraph) for paragraph in reversed(paragraphs)
                     if len(paragraph) < 450 and any(keyword in normalize_name(paragraph) for keyword in VENUES)), "")
    venue = next((name for keyword, name in VENUES.items() if keyword in location), None)
    if not venue:
        raise SourceError(f"{record['source_url']}: no explicit venue")
    start, end = record["date"], record["end_date"]
    dates = [start]
    name = normalize_name(record["name"])
    if "domingos com musica" in name:
        dates = [start + dt.timedelta(days=offset) for offset in range((end - start).days + 1)
                 if (start + dt.timedelta(days=offset)).weekday() == 6]
    elif "oficina" in name and end > start:
        if "duas sessoes" not in text:
            raise SourceError(f"{record['source_url']}: workshop range lacks discrete session dates")
        dates = [start, end]
    if "oficina" in name and "duas sessoes" in text:
        second = re.search(r"segunda sess[aã]o[^.]*?(\d{1,2}\s+de\s+\w+)", description, re.I)
        if second:
            next_date = published_dates(second[1], start.year)[0][0]
            if next_date > start:
                dates = [start, next_date]
    if not dates:
        raise SourceError(f"{record['source_url']}: date range contains no stated weekday session")
    events = []
    for date in dates:
        event = dict(record, date=date, venue=venue,
                     time=None if "/exhibitions/" in record["source_url"] else published_time(location),
                     description=clean_description(description),
                     source_uid=f"{record['source_url']}#{date.isoformat()}",
                     tags=list(dict.fromkeys(record.get("tags", []) + _tags_for(record["name"], description))))
        if len(dates) > 1 or end <= date:
            event.pop("end_date", None)
        events.append(event)
    return events


def discover_events(today: dt.date, lookahead: dt.date, health: SourceHealth) -> list[dict]:
    """Fetch every archive page and current dated details, failing on incomplete coverage."""
    pending, visited, sessions, details, events = list(ARCHIVES), set(), set(), {}, []
    while pending:
        url = pending.pop(0)
        if url in visited:
            continue
        if len(visited) >= MAX_PAGES:
            raise SourceError("Museum archive pagination cap reached")
        records, pages = parse_archive(health.fetch(url), url)
        visited.add(url)
        pending.extend(page for page in pages if page not in visited and page not in pending)
        for record in records:
            identity = (record["source_url"], record["date"], record["end_date"])
            if identity in sessions:
                continue
            sessions.add(identity)
            health.listed += 1
            if record["end_date"] < today or record["date"] > lookahead:
                continue
            health.local += 1
            if record["source_url"] not in details:
                details[record["source_url"]] = health.fetch(record["source_url"])
            parsed = parse_detail(details[record["source_url"]], record)
            if not parsed:
                health.rejected += 1
                health.warnings.append(f"Restricted continuation workshop: {record['source_url']}")
            health.parsed += len(parsed)
            events.extend(parsed)
    return events


def main() -> int:
    return run_ingester("Museu de Angra", discover_events)


if __name__ == "__main__":
    sys.exit(main())
