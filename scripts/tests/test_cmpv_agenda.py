"""Regression tests for the CMPV agenda HTML ingester.

The live agenda is plain server-rendered HTML at
``https://www.cmpv.pt/index.php?op=agenda`` (cards with ``.nomeAgenda`` /
``.dataAgenda`` spans, detail links ``index.php?op=agenda&...&id=NNN`` and
``.link_paginacao_opcoes`` pagination links). Guessed-feed fallbacks must
not return: every failure below raises ``SourceError`` instead of
succeeding quietly.

Run from the repo root:

    /tmp/terceira-scan-venv/bin/python -m unittest scripts.tests.test_cmpv_agenda -v
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import unittest
import urllib.parse

# Allow `from ingest_* import ...` whether run from repo root or from
# scripts/tests/ directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

import ingest_cmpv
from ingest_cmpv import SourceError

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "cmpv")


def fixture(name: str) -> bytes:
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return f.read()


def detail_url(event_id: str) -> str:
    return urllib.parse.urljoin(
        ingest_cmpv.AGENDA_URL, f"index.php?op=agenda&id={event_id}"
    )


def page_url(pag: int) -> str:
    return urllib.parse.urljoin(
        ingest_cmpv.AGENDA_URL,
        f"index.php?op=agenda&catid=&pag={pag}&next_ecran=1&pag_ant=",
    )


class FakeHealth:
    """Stand-in for SourceHealth with the same counters and fetch contract."""

    def __init__(self, pages: dict):
        self._pages = pages
        self.pages = 0
        self.listed = 0
        self.local = 0
        self.parsed = 0
        self.rejected = 0
        self.warnings: list = []
        self.fetched: list = []

    def fetch(self, url: str) -> bytes:
        self.fetched.append(url)
        if url not in self._pages:
            raise SourceError(f"404 for {url}")
        payload = self._pages[url]
        if isinstance(payload, Exception):
            raise payload
        self.pages += 1
        return payload


class DiscoverTests(unittest.TestCase):
    def setUp(self):
        self.today = dt.date(2026, 10, 10)
        self.lookahead = self.today + dt.timedelta(days=365)
        self.pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_p1.html"),
            page_url(1): fixture("agenda_p1.html"),
            page_url(2): fixture("agenda_p2.html"),
            detail_url("913"): fixture("detail_913.html"),
            detail_url("914"): fixture("detail_914.html"),
            detail_url("918"): fixture("detail_918.html"),
            detail_url("819"): fixture("detail_819.html"),
            detail_url("909"): fixture("detail_909.html"),
            detail_url("911"): fixture("detail_911.html"),
        }

    def discover(self, pages=None, today=None):
        health = FakeHealth(pages if pages is not None else self.pages)
        events = ingest_cmpv.discover_events(
            today or self.today, self.lookahead, health
        )
        return events, health

    def range_pages(self):
        return {
            ingest_cmpv.AGENDA_URL: fixture("agenda_range.html"),
            page_url(1): fixture("agenda_range.html"),
            detail_url("920"): fixture("detail_920.html"),
            detail_url("921"): fixture("detail_921.html"),
        }

    def single_pages(self, detail_fixture):
        return {
            ingest_cmpv.AGENDA_URL: fixture("agenda_single.html"),
            page_url(1): fixture("agenda_single.html"),
            detail_url("914"): fixture(detail_fixture),
        }

    def test_films_and_show_discovered_across_pagination(self):
        events, health = self.discover()
        names = sorted(e["name"] for e in events)
        self.assertIn("Verity", names)
        self.assertIn("A Ovelha Choné: Trapalhada na Quinta", names)
        self.assertIn('Hugo Sousa - "Aqui Entre Nós"', names)
        self.assertIn("ISTO NÃO É GOSTAR DE PODCASTS - Ao vivo", names)
        self.assertIn(
            "Jornadas do Mar - \"Oceano Sustentável: Conhecer, Proteger, Agir\"",
            names,
        )
        # Both agenda pages were followed.
        self.assertIn(page_url(2), health.fetched)
        # Counters reconcile against unique card IDs: 8 listed across both
        # pages (base URL repeats page 1), 6 in-window, 6 parsed, 2 touradas
        # excluded.
        self.assertEqual(health.listed, 8)
        self.assertEqual(health.local, 6)
        self.assertEqual(health.parsed, len(events))
        self.assertEqual(len(events), 6)
        self.assertEqual(health.rejected, 2)

    def test_same_film_on_two_dates_not_collapsed(self):
        events, _ = self.discover()
        verity = [e for e in events if e["name"] == "Verity"]
        self.assertEqual(len(verity), 2)
        dates = sorted(e["date"] for e in verity)
        self.assertEqual(dates, [dt.date(2026, 10, 23), dt.date(2026, 10, 24)])
        uids = {e["source_uid"] for e in verity}
        self.assertEqual(len(uids), 2, "each screening needs a stable distinct uid")

    def test_touradas_excluded_without_detail_fetch(self):
        events, health = self.discover()
        for e in events:
            self.assertNotRegex(e["name"].lower(), r"tourada|vacada|bezerrada")
            self.assertNotIn("bullfighting", e["tags"])
        for excluded in ("895", "908"):
            self.assertNotIn(
                detail_url(excluded),
                health.fetched,
                f"tourada detail {excluded} must not be fetched",
            )

    def test_venue_verified_from_detail(self):
        events, _ = self.discover()
        verity = [e for e in events if e["source_uid"].startswith("cmpv-914-")][0]
        self.assertEqual(verity["venue"], "Auditório do Ramo Grande")
        jornadas = [e for e in events if "Jornadas do Mar" in e["name"]][0]
        self.assertEqual(
            jornadas["venue"],
            "Auditório da Escola Profissional da Praia da Vitória",
        )

    def test_time_extracted_from_detail(self):
        events, _ = self.discover()
        hugo = [e for e in events if "Hugo Sousa" in e["name"]][0]
        self.assertEqual(hugo["time"], "21:30")
        self.assertEqual(hugo["date"], dt.date(2026, 10, 24))

    def test_tags_canonical_and_no_price_or_eligibility_inferred(self):
        events, _ = self.discover()
        vocab = {
            "kid-friendly", "live-music", "cinema", "theater", "dance",
            "nightlife", "karaoke", "food-drink", "exhibition", "literature",
            "workshop", "free", "outdoor", "bullfighting",
        }
        for e in events:
            for tag in e["tags"]:
                self.assertIn(tag, vocab)
            self.assertNotIn("free", e["tags"])
            self.assertNotIn("price", e)
        verity = [e for e in events if e["name"] == "Verity"][0]
        self.assertIn("cinema", verity["tags"])
        chone = [e for e in events if "Choné" in e["name"]][0]
        self.assertIn("cinema", chone["tags"])
        self.assertIn("kid-friendly", chone["tags"])

    def test_empty_recognized_agenda_returns_empty(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_empty.html"),
            page_url(1): fixture("agenda_empty.html"),
        }
        events, health = self.discover(pages)
        self.assertEqual(events, [])
        self.assertEqual(health.listed, 0)

    def test_non_agenda_page_raises(self):
        pages = {ingest_cmpv.AGENDA_URL: fixture("non_agenda.html")}
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_http_failure_raises(self):
        health = FakeHealth({})
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_broken_detail_page_raises(self):
        pages = dict(self.pages)
        pages[detail_url("914")] = SourceError("404 for detail")
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_login_detail_page_raises(self):
        pages = dict(self.pages)
        pages[detail_url("914")] = fixture("non_agenda.html")
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_genuine_card_with_invalid_date_raises(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_malformed.html"),
            page_url(1): fixture("agenda_malformed.html"),
            detail_url("914"): fixture("detail_914.html"),
        }
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_tooltip_fragment_without_id_is_ignored(self):
        # The calendar tooltip markup lives in a title attribute and never
        # parses as elements, so only the genuine card resolves.
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_tooltip.html"),
            page_url(1): fixture("agenda_tooltip.html"),
            detail_url("914"): fixture("detail_914.html"),
        }
        events, health = self.discover(pages)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["name"], "Verity")
        self.assertEqual(health.listed, 1)
        self.assertEqual(health.rejected, 0)

    def test_card_without_bootstrap_container_class_is_found(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_mb3.html"),
            page_url(1): fixture("agenda_mb3.html"),
            detail_url("914"): fixture("detail_914.html"),
        }
        events, _ = self.discover(pages)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["name"], "Verity")

    def test_unconsumed_name_date_spans_raise(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_stray.html"),
            page_url(1): fixture("agenda_stray.html"),
            detail_url("914"): fixture("detail_914.html"),
        }
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_pagination_without_calendar_is_not_an_empty_agenda(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_pagonly.html"),
            page_url(1): fixture("agenda_pagonly.html"),
        }
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_renamed_card_spans_raise(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_renamed.html"),
            page_url(1): fixture("agenda_renamed.html"),
        }
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_calendar_id_without_card_raises(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_cal_only.html"),
            page_url(1): fixture("agenda_cal_only.html"),
            detail_url("914"): fixture("detail_914.html"),
        }
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_calendar_attribute_id_without_card_raises(self):
        # The calendar cell carries only data-aulaId="999"; its anchor has
        # no id. The advertised 999 must still enforce the coverage check.
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_cal_attr.html"),
            page_url(1): fixture("agenda_cal_attr.html"),
            detail_url("914"): fixture("detail_914.html"),
        }
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_office_hours_are_not_a_show_time(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_single.html"),
            page_url(1): fixture("agenda_single.html"),
            detail_url("914"): fixture("detail_notime.html"),
        }
        events, _ = self.discover(pages)
        self.assertEqual(len(events), 1)
        self.assertNotIn("time", events[0])

    def test_duration_is_not_a_show_time(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_p1.html"),
            page_url(1): fixture("agenda_p1.html"),
            page_url(2): fixture("agenda_p2.html"),
            detail_url("913"): fixture("detail_duration.html"),
            detail_url("914"): fixture("detail_914.html"),
            detail_url("918"): fixture("detail_918.html"),
            detail_url("819"): fixture("detail_819.html"),
            detail_url("909"): fixture("detail_909.html"),
            detail_url("911"): fixture("detail_911.html"),
        }
        events, _ = self.discover(pages)
        chone = [e for e in events if "Choné" in e["name"]][0]
        self.assertNotIn("time", chone)

    def test_contradictory_duplicate_id_raises(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_p1.html"),
            page_url(1): fixture("agenda_p1.html"),
            page_url(2): fixture("agenda_conflict.html"),
            detail_url("913"): fixture("detail_913.html"),
            detail_url("914"): fixture("detail_914.html"),
            detail_url("918"): fixture("detail_918.html"),
            detail_url("819"): fixture("detail_819.html"),
        }
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_range_event_keeps_end_date(self):
        events, health = self.discover(
            self.range_pages(), today=dt.date(2026, 10, 1)
        )
        self.assertEqual(len(events), 2)
        first = [e for e in events if e["source_uid"].startswith("cmpv-920-")][0]
        self.assertEqual(first["date"], dt.date(2026, 10, 2))
        self.assertEqual(first["end_date"], dt.date(2026, 10, 4))
        self.assertEqual(first["source_uid"], "cmpv-920-2026-10-02")
        self.assertIn("exhibition", first["tags"])
        self.assertEqual(first["time"], "10:00")
        self.assertEqual(health.listed, 2)
        self.assertEqual(health.parsed, 2)

    def test_ongoing_range_with_past_start_is_kept(self):
        events, _ = self.discover(self.range_pages())
        second = [e for e in events if e["source_uid"].startswith("cmpv-921-")]
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]["date"], dt.date(2026, 10, 8))
        self.assertEqual(second[0]["end_date"], dt.date(2026, 10, 15))

    def test_venue_skips_ticket_boilerplate(self):
        events, _ = self.discover(self.single_pages("detail_venue_ticket.html"))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["venue"], "Auditório do Ramo Grande")

    def test_venue_skips_description_prose(self):
        events, _ = self.discover(self.single_pages("detail_venue_casa.html"))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["venue"], "Auditório do Ramo Grande")

    def test_age_rating_tags(self):
        young = ingest_cmpv._map_detail_tags("Filme X", "Sessão M/3 Versão Portuguesa")
        self.assertIn("cinema", young)
        self.assertIn("kid-friendly", young)
        teen = ingest_cmpv._map_detail_tags("Filme Y", "M/16 Versão Original Legendada")
        self.assertIn("cinema", teen)
        self.assertNotIn("kid-friendly", teen)

    def test_invalid_minutes_do_not_survive(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_hugo.html"),
            page_url(1): fixture("agenda_hugo.html"),
            detail_url("819"): fixture("detail_badtime.html"),
        }
        events, _ = self.discover(pages)
        self.assertEqual(len(events), 1)
        self.assertNotIn("time", events[0])

    def test_unverified_venue_raises(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_single.html"),
            page_url(1): fixture("agenda_single.html"),
            detail_url("914"): fixture("detail_novenue.html"),
        }
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_detail_date_mismatch_raises(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_single.html"),
            page_url(1): fixture("agenda_single.html"),
            detail_url("914"): fixture("detail_wrongdate.html"),
        }
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)

    def test_foreign_card_link_raises(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_foreign_card.html"),
            page_url(1): fixture("agenda_foreign_card.html"),
        }
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)
        self.assertFalse(
            [u for u in health.fetched if "example.test" in u],
            "no foreign URL may be fetched",
        )

    def test_foreign_pagination_link_raises(self):
        pages = {
            ingest_cmpv.AGENDA_URL: fixture("agenda_foreign_page.html"),
            page_url(1): fixture("agenda_foreign_page.html"),
            detail_url("914"): fixture("detail_914.html"),
        }
        health = FakeHealth(pages)
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)
        self.assertFalse(
            [u for u in health.fetched if "example.test" in u],
            "no foreign URL may be fetched",
        )

    def test_pagination_cap_raises(self):
        # Every page advertises one more unvisited page: the crawl must stop
        # with a visible error instead of paging forever.
        health = FakeHealth({})

        def endless_fetch(url: str) -> bytes:
            query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            try:
                n = int(query.get("pag", ["1"])[0])
            except ValueError:
                n = 1
            return (
                "<html><head><title>Câmara Municipal da Praia da Vitória</title></head>"
                "<body><div class='col-12 pt-4 pb-4'><ul class='paginacao'>"
                f"<li><a class='link_paginacao_opcoes' href='index.php?op=agenda&catid=&pag={n + 1}&next_ecran=1&pag_ant='>{n + 1}</a></li>"
                "</ul></div></body></html>"
            ).encode("utf-8")

        health.fetch = endless_fetch  # type: ignore[assignment]
        with self.assertRaises(SourceError):
            ingest_cmpv.discover_events(self.today, self.lookahead, health)


if __name__ == "__main__":
    unittest.main()
