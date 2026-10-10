#!/usr/bin/env python3
"""Ingest events from the Câmara Municipal da Praia da Vitória agenda.

Source: https://www.cmpv.pt/index.php?op=agenda

The public agenda is server-rendered HTML: listing cards with
``.nomeAgenda`` / ``.dataAgenda`` spans, detail links of the form
``index.php?op=agenda&...&id=NNN``, and ``.link_paginacao_opcoes``
pagination links. Discovery crawls those links (bounded by
``MAX_PAGES``), then resolves each listed card through its detail page,
which verifies the venue and provides time, description and tags.
Listing dates may span an explicit range such as ``2 a 4 outubro``; the
event keeps the range's ``end_date`` and stays listed while ongoing.

Bullfighting listings are left to the tourada ingester. Prices and
eligibility are never inferred: the ``free`` tag is never emitted. Each
screening keeps a date-qualified ``source_uid`` so repeat screenings on
different dates stay distinct.

Any incomplete coverage raises ``SourceError``: HTTP failure,
unrecognizable pages, broken detail pages, genuine cards with invalid
dates or unverified venues, detail dates disagreeing with the listing,
contradictory duplicate ids, links leaving the CMPV agenda route, and
pagination loops or caps. Every event the calendar widget advertises
must resolve to a listing card. A recognized agenda that lists nothing — with
the calendar and pagination chrome present and no unconsumed agenda
markup — succeeds with no events.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import urllib.parse

from ingest_common import build_map_url, clean_description, normalize_name
from ingest_dates import MONTHS, published_dates, published_time
from ingest_health import SourceError, SourceHealth, run_ingester
from ingest_html import HtmlNode, parse_html

BASE_URL = "https://www.cmpv.pt"
AGENDA_URL = f"{BASE_URL}/index.php?op=agenda"
AGENDA_HOST = urllib.parse.urlparse(BASE_URL).hostname

# The live agenda fits on two pages; anything beyond this is a loop.
MAX_PAGES = 10

DEFAULT_LOCALITY = "Praia da Vitória"

EVENT_ID_RE = re.compile(r"[?&]id=(\d+)")

TOURADA_RE = re.compile(
    r"\b(tourada|touradas|toirada|toiradas|vacada|vacadas|bezerrada|garraio)\b",
    re.IGNORECASE,
)

VENUE_RE = re.compile(
    r"auditório|teatro|museu|largo|praça|pavilhão|escola|centro cultural|"
    r"biblioteca|igreja|galeria|jardim|anfiteatro|salão|avenida|"
    r"\brua\b|travessa",
    re.IGNORECASE,
)

TICKET_RE = re.compile(r"bilhet|ticketline|ajait|bilheteira|à venda", re.IGNORECASE)
ORGANIZER_RE = re.compile(
    r"^(produção|producao|apoio|organização|organizacao|org\.?|promotor)\s*:",
    re.IGNORECASE,
)
METADATA_RE = re.compile(
    r"^(género|genero|duração|duracao|m/\d+)\s*:", re.IGNORECASE
)

AGENDA_CLASSES = frozenset({
    "nomeAgenda", "dataAgenda", "paginacao", "link_paginacao_opcoes",
    "wDayData", "wDayDataAtivo",
})
CALENDAR_CLASSES = frozenset({"wDayData", "wDayDataAtivo"})
PAGINATION_CLASSES = frozenset({"paginacao", "link_paginacao_opcoes"})
CALENDAR_TAGS = frozenset({"table", "tbody", "thead", "tr", "td"})

_BLOCK_TAGS = frozenset({
    "div", "p", "br", "li", "tr", "ul", "ol", "table",
    "h1", "h2", "h3", "h4",
})

_FILLER_WORDS = frozenset(MONTHS) | {
    "de", "da", "do", "das", "dos", "a", "e", "em", "no", "na",
    "segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo",
    "feira", "seg", "ter", "qua", "qui", "sex", "sab", "dom",
}
_TIME_TOKEN_RE = re.compile(r"(?<!\d)([01]?\d|2[0-3])\s*[:hH]\s*[0-5]?\d(?!\d)")
_LEADING_PREP_RE = re.compile(r"^(?:de|desde|entre)\s+", re.IGNORECASE)


def detail_url(event_id: str) -> str:
    """Return the absolute public detail URL for an agenda id."""
    return urllib.parse.urljoin(AGENDA_URL, f"index.php?op=agenda&id={event_id}")


def _agenda_url(href: str, base: str) -> str:
    """Resolve a listing link, keeping every followed URL on the agenda route."""
    absolute = urllib.parse.urljoin(base, href)
    parts = urllib.parse.urlparse(absolute)
    query = urllib.parse.parse_qs(parts.query)
    if (
        parts.scheme not in ("http", "https")
        or parts.hostname != AGENDA_HOST
        or parts.path != "/index.php"
        or query.get("op") != ["agenda"]
    ):
        raise SourceError(f"link leaves the CMPV agenda: {href}")
    return absolute


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _page_classes(root: HtmlNode) -> set:
    classes: set = set()
    for node in root.walk():
        classes.update((node.attrs.get("class") or "").split())
    return classes


def _listing_cards(root: HtmlNode, page_url: str) -> tuple:
    """Read (event_id, name, date_text) triples from genuine cards.

    A card is an agenda link with a numeric id whose surrounding markup
    carries the title/date spans, regardless of container classes. An
    agenda link that cannot be consumed as a card is renamed-markup
    failure, unless it sits inside the calendar, whose tooltip residue
    lives in attributes or table cells and is ignored here.
    """
    parents: dict = {}
    for node in root.walk():
        for child in node.children:
            if isinstance(child, HtmlNode):
                parents[id(child)] = node

    def in_calendar(node: HtmlNode) -> bool:
        current = parents.get(id(node))
        while current is not None:
            if current.tag in CALENDAR_TAGS:
                return True
            current = parents.get(id(current))
        return False

    cards = []
    consumed: set = set()
    for anchor in root.walk():
        if anchor.tag != "a":
            continue
        href = anchor.attrs.get("href") or ""
        classes = anchor.attrs.get("class") or ""
        if "link_paginacao" in classes or "wDayData" in classes:
            continue
        match = EVENT_ID_RE.search(href)
        if not match:
            continue
        container = None
        node = parents.get(id(anchor))
        while node is not None and node.tag != "root":
            if any(
                child.tag == "span" and child.has_class("nomeAgenda")
                for child in node.walk()
            ):
                container = node
                break
            node = parents.get(id(node))
        if container is None:
            if in_calendar(anchor):
                continue
            raise SourceError(
                f"{page_url}: agenda link {match.group(1)} "
                "cannot be consumed as a card"
            )
        _agenda_url(href, page_url)
        name_nodes = [
            child for child in container.walk()
            if child.tag == "span" and child.has_class("nomeAgenda")
        ]
        date_nodes = [
            child for child in container.walk()
            if child.tag == "span" and child.has_class("dataAgenda")
        ]
        if not name_nodes or not date_nodes:
            raise SourceError(
                f"{page_url}: agenda card {match.group(1)} lacks a title or date"
            )
        consumed.add(id(name_nodes[0]))
        consumed.add(id(date_nodes[0]))
        cards.append((match.group(1), name_nodes[0].text(), date_nodes[0].text()))

    stray = [
        _collapse(node.text()) for node in root.walk()
        if node.tag == "span"
        and (node.has_class("nomeAgenda") or node.has_class("dataAgenda"))
        and id(node) not in consumed
        and not in_calendar(node)
    ]
    return cards, stray


def _calendar_ids(root: HtmlNode) -> set:
    """Collect event ids advertised by the calendar widget, if any."""
    ids = set()
    for node in root.walk():
        # html.parser lowercases attribute names, so data-aulaId reads back
        # as data-aulaid.
        aula = node.attrs.get("data-aulaid") or ""
        if aula.isdigit():
            ids.add(aula)
        if node.tag == "a" and "wDayData" in (node.attrs.get("class") or ""):
            match = EVENT_ID_RE.search(node.attrs.get("href") or "")
            if match:
                ids.add(match.group(1))
    return ids


def _pagination_hrefs(root: HtmlNode, page_url: str) -> list:
    hrefs = []
    for node in root.walk():
        if node.tag == "a" and node.has_class("link_paginacao_opcoes"):
            href = node.attrs.get("href") or ""
            if href:
                hrefs.append(_agenda_url(href, page_url))
    return hrefs


def _listing_range(date_text: str, year: int) -> tuple:
    """Return the single (start, end) session of a listing date label."""
    try:
        sessions = published_dates(date_text, year)
    except ValueError as exc:
        raise SourceError(f"unrecognized agenda date {date_text!r}: {exc}") from exc
    if len(sessions) != 1:
        raise SourceError(f"ambiguous agenda date: {date_text!r}")
    return sessions[0]


def _detail_range(lines: list, year: int) -> tuple | None:
    """Return the event's date range from its detail label, if any is printed."""
    for line in lines:
        try:
            sessions = published_dates(_LEADING_PREP_RE.sub("", line), year)
        except ValueError:
            continue
        if len(sessions) != 1:
            raise SourceError(f"detail date is ambiguous: {line!r}")
        return sessions[0]
    return None


def _detail_lines(node: HtmlNode) -> list:
    chunks: list = []

    def visit(current: HtmlNode | str) -> None:
        if isinstance(current, str):
            chunks.append(current)
            return
        if current.tag in ("script", "style"):
            return
        if current.tag in _BLOCK_TAGS:
            chunks.append("\n")
        for child in current.children:
            visit(child)
        if current.tag in _BLOCK_TAGS and current.tag != "br":
            chunks.append("\n")

    visit(node)
    text = "".join(chunks).replace("\xa0", " ")
    return [line.strip() for line in text.split("\n") if line.strip()]


def _parse_detail(payload: bytes, url: str) -> tuple:
    """Return (title, body_lines) for a detail page."""
    root = parse_html(payload)
    titles = [
        _collapse(node.text())
        for node in root.walk()
        if node.tag == "span" and node.has_class("titulos")
    ]
    titles = [title for title in titles if not title.lower().startswith("agenda")]
    if not titles:
        raise SourceError(f"detail page has no event title: {url}")
    bodies = [
        node
        for node in root.walk()
        if node.tag == "span" and node.has_class("textos")
    ]
    if not bodies:
        raise SourceError(f"detail page has no event body: {url}")
    lines = _detail_lines(bodies[0])
    if not lines:
        raise SourceError(f"detail page has no event body: {url}")
    return titles[0], lines


def _find_venue(lines: list) -> str:
    """Return the first explicit venue line, skipping sales and metadata lines."""
    for line in lines:
        if TICKET_RE.search(line):
            continue
        if ORGANIZER_RE.match(line):
            continue
        if METADATA_RE.match(line):
            continue
        if VENUE_RE.search(line):
            return _collapse(line)
    return ""


def _find_time(lines: list) -> str | None:
    """Return the session time printed in the detail body, if any is shown."""
    return published_time("\n".join(lines))


def _map_detail_tags(title: str, body_text: str) -> list:
    blob = f"{title}\n{body_text}".lower()
    tags: list = []

    def add(slug: str) -> None:
        if slug not in tags:
            tags.append(slug)

    if re.search(r"género:|duração:|\bm/\d+|versão original|versão portuguesa", blob):
        add("cinema")
    if re.search(r"stand.?up|comédia|comedy", blob):
        add("theater")
    if re.search(r"\bconcerto|\bmúsica|\bbanda|\bfilar", blob):
        add("live-music")
    if re.search(r"\bteatro\b", blob):
        add("theater")
    if re.search(r"\bdança\b", blob):
        add("dance")
    if re.search(r"\bexposi|mostra\b", blob):
        add("exhibition")
    if re.search(r"\bworkshop|\boficina\b", blob):
        add("workshop")
    if re.search(r"\blivro|literatura|poesia|\bleitura\b", blob):
        add("literature")
    if re.search(r"infantil|criança|família|\bm/[36]\b|animação", blob):
        add("kid-friendly")
    return tags


def _is_date_or_time_line(line: str, year: int) -> bool:
    candidate = _TIME_TOKEN_RE.sub(" ", _LEADING_PREP_RE.sub("", line))
    try:
        published_dates(candidate, year)
    except ValueError:
        return False
    words = re.findall(r"[^\W\d_]+", normalize_name(candidate).lower())
    return bool(words) and all(word in _FILLER_WORDS for word in words)


def _build_description(title: str, venue: str, lines: list, year: int) -> str:
    kept = []
    for line in lines:
        if line == title or line == venue:
            continue
        if TICKET_RE.search(line):
            continue
        if _is_date_or_time_line(line, year):
            continue
        kept.append(line)
    return clean_description(" ".join(kept))


def discover_events(today: dt.date, lookahead: dt.date, health: SourceHealth) -> list:
    """Crawl the live agenda and return verified event dicts.

    ``health.listed`` counts unique card ids seen, ``health.local`` the
    in-window ids sent for detail resolution, ``health.parsed`` the
    events returned, and ``health.rejected`` the bullfighting exclusions.
    """
    seen: dict = {}
    advertised: set = set()
    queue = [AGENDA_URL]
    visited: set = set()
    seed_root: HtmlNode | None = None
    while queue:
        url = queue.pop(0)
        if url in visited:
            continue
        if len(visited) >= MAX_PAGES:
            raise SourceError(
                f"pagination cap exceeded ({MAX_PAGES} pages from {AGENDA_URL})"
            )
        root = parse_html(health.fetch(url))
        visited.add(url)
        if seed_root is None:
            seed_root = root
        if not (_page_classes(root) & AGENDA_CLASSES):
            raise SourceError(f"page is not a recognizable agenda: {url}")
        cards, stray = _listing_cards(root, url)
        if stray:
            raise SourceError(
                f"{url}: unconsumed agenda markup: {stray[0][:80]!r}"
            )
        advertised.update(_calendar_ids(root))
        for event_id, name, date_text in cards:
            key = (_collapse(name), _collapse(date_text))
            if event_id in seen and seen[event_id] != key:
                raise SourceError(
                    f"agenda id {event_id} lists contradictory entries: "
                    f"{seen[event_id][0]!r} vs {key[0]!r}"
                )
            seen.setdefault(event_id, key)
        for href in _pagination_hrefs(root, url):
            if href not in visited and href not in queue:
                queue.append(href)

    missing = sorted(advertised - set(seen), key=int)
    if missing:
        raise SourceError(
            f"calendar advertises events without listing cards: {', '.join(missing)}"
        )
    if not seen:
        classes = _page_classes(seed_root) if seed_root is not None else set()
        if not (classes & CALENDAR_CLASSES and classes & PAGINATION_CLASSES):
            raise SourceError(f"page is not a recognizable agenda: {AGENDA_URL}")
        return []

    events: list = []
    for event_id, (raw_name, date_text) in seen.items():
        name = _collapse(raw_name)
        if not name:
            raise SourceError(f"{AGENDA_URL}: agenda card {event_id} has no title")
        health.listed += 1
        if TOURADA_RE.search(name):
            health.rejected += 1
            health.warnings.append(f"{name}: bullfighting, owned by the tourada ingester")
            continue
        start, end = _listing_range(date_text, today.year)
        if end < today or start > lookahead:
            continue
        health.local += 1
        url = detail_url(event_id)
        try:
            payload = health.fetch(url)
        except SourceError as exc:
            raise SourceError(f"required detail page failed for {name!r}: {exc}") from exc
        title, lines = _parse_detail(payload, url)
        venue = _find_venue(lines)
        if not venue:
            raise SourceError(f"{title!r}: detail verifies no venue")
        detail_session = _detail_range(lines, start.year)
        if detail_session is not None and detail_session != (start, end):
            raise SourceError(
                f"{title!r}: detail date disagrees with listing "
                f"{start.isoformat()}..{end.isoformat()}"
            )
        body_text = "\n".join(lines)
        event = {
            "date": start,
            "name": title,
            "venue": venue.partition(",")[0].strip() or venue,
            "address": venue.partition(",")[2].strip(),
            "map_url": build_map_url(
                venue.partition(",")[0].strip() or venue, DEFAULT_LOCALITY
            ),
            "description": _build_description(title, venue, lines, start.year),
            "source_url": url,
            "source_uid": f"cmpv-{event_id}-{start.isoformat()}",
            "tags": _map_detail_tags(title, body_text),
        }
        if end > start:
            event["end_date"] = end
        found_time = _find_time(lines)
        if found_time is not None:
            event["time"] = found_time
        events.append(event)
        health.parsed += 1
    return events


def main() -> int:
    return run_ingester("CMPV", discover_events)


if __name__ == "__main__":
    sys.exit(main())
