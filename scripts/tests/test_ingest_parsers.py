"""Unit tests for the ingest parsers.

Each ingest script does its own HTTP fetching but the parsing logic is
pure and can be exercised in isolation against synthetic fixtures. These
tests pin the parser behaviour so changes to the fixtures (sample REST
payloads, iCal blobs, JSON-LD blocks) fail loudly rather than silently
ingesting garbage.

Run from the repo root:

    python -m unittest scripts.tests.test_ingest_parsers -v
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import textwrap
import unittest

# Allow `from ingest_* import ...` whether run from repo root or from
# scripts/tests/ directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

import ingest_jsonld
import ingest_museu_angra
import ingest_cmpv
import ingest_touradas


class MuseumRestParserTests(unittest.TestCase):
    def test_rest_event_with_full_venue(self):
        payload = json.dumps({
            "events": [{
                "id": 12345,
                "title": "Domingos com Música — Tertúlia",
                "start_date": "2026-05-31 11:00:00",
                "venue": {
                    "venue": "Museu de Angra do Heroísmo",
                    "address": "Ladeira de São Francisco",
                    "zip": "9700-182",
                    "city": "Angra do Heroísmo",
                },
                "description": "Concerto matinal no claustro",
                "url": "https://museu-angra.cultura.azores.gov.pt/events/dom-musica/",
            }]
        }).encode("utf-8")
        out = ingest_museu_angra._parse_rest_api(payload)
        self.assertEqual(len(out), 1)
        ev = out[0]
        self.assertEqual(ev["date"], dt.date(2026, 5, 31))
        self.assertEqual(ev["time"], "11:00")
        self.assertEqual(ev["source_uid"], "12345@museu-angra.cultura.azores.gov.pt")
        self.assertIn("live-music", ev["tags"])
        self.assertIn("exhibition", ev["tags"])  # default tag

    def test_rest_event_with_all_day_start(self):
        payload = json.dumps({
            "events": [{
                "id": 7,
                "title": "Exposição: Olhar o Outro",
                "start_date": "2026-06-01 00:00:00",
                "description": "",
            }]
        }).encode("utf-8")
        out = ingest_museu_angra._parse_rest_api(payload)
        self.assertEqual(out[0]["time"], None, "midnight starts should be treated as all-day")

    def test_rest_garbage_payload_returns_empty(self):
        self.assertEqual(ingest_museu_angra._parse_rest_api(b"<html>not json</html>"), [])
        self.assertEqual(ingest_museu_angra._parse_rest_api(b"{}"), [])


class MuseumIcalParserTests(unittest.TestCase):
    def test_ical_event_with_workshop_keywords(self):
        ical_text = textwrap.dedent(
            """\
            BEGIN:VCALENDAR
            VERSION:2.0
            BEGIN:VEVENT
            UID:99@museu
            SUMMARY:Oficina para Famílias - Pinturas
            DTSTART:20260601T160000
            LOCATION:Museu de Angra do Heroísmo, Ladeira de São Francisco
            DESCRIPTION:Oficina infantil
            URL:https://museu-angra.cultura.azores.gov.pt/events/oficina/
            END:VEVENT
            END:VCALENDAR
            """
        ).encode("utf-8")
        out = ingest_museu_angra._parse_ical(ical_text)
        self.assertEqual(len(out), 1)
        ev = out[0]
        self.assertEqual(ev["time"], "16:00")
        self.assertIn("workshop", ev["tags"])
        self.assertIn("kid-friendly", ev["tags"])


class CmpvIcalParserTests(unittest.TestCase):
    def test_event_with_categories(self):
        # Build via icalendar to get exact-format bytes the parser expects.
        import icalendar
        cal = icalendar.Calendar()
        cal.add("prodid", "-//test//pt")
        cal.add("version", "2.0")
        event = icalendar.Event()
        event.add("uid", "111@cmpv.pt")
        event.add("summary", "Cinema: Filme X")
        event.add("dtstart", dt.datetime(2026, 6, 10, 21, 30))
        event.add("location", "Auditório Ramo Grande, Praia da Vitória, 9760")
        event.add("description", "Sessão de cinema.")
        event.add("categories", ["Cinema"])
        cal.add_component(event)
        vevents = list(icalendar.Calendar.from_ical(cal.to_ical()).walk("VEVENT"))
        component = vevents[0]
        date, time = ingest_cmpv._extract_date_time(component.get("DTSTART"))
        self.assertEqual(date, dt.date(2026, 6, 10))
        self.assertEqual(time, "21:30")
        venue, address = ingest_cmpv._split_location(str(component.get("LOCATION")))
        self.assertEqual(venue, "Auditório Ramo Grande")
        self.assertIn("Praia da Vitória", address)
        tags = ingest_cmpv._map_tags(component.get("CATEGORIES"))
        self.assertEqual(tags, ["cinema"])

    def test_all_day_dtstart_strips_time(self):
        import icalendar
        cal = icalendar.Calendar()
        cal.add("prodid", "-//t//pt")
        cal.add("version", "2.0")
        ev = icalendar.Event()
        ev.add("uid", "ad@cmpv")
        ev.add("summary", "Feriado")
        ev.add("dtstart", dt.date(2026, 6, 10))
        cal.add_component(ev)
        component = list(icalendar.Calendar.from_ical(cal.to_ical()).walk("VEVENT"))[0]
        date, time = ingest_cmpv._extract_date_time(component.get("DTSTART"))
        self.assertEqual(date, dt.date(2026, 6, 10))
        self.assertIsNone(time)


class JsonLdHarvesterTests(unittest.TestCase):
    def test_extracts_single_event_block(self):
        html = textwrap.dedent(
            """\
            <html><head><script type="application/ld+json">
            {"@type": "Event", "name": "Concerto em Terceira",
             "startDate": "2026-07-15T21:00",
             "location": {"name": "Teatro Angrense",
                          "address": {"streetAddress": "Rua X",
                                      "addressLocality": "Angra do Heroísmo",
                                      "postalCode": "9700-073"}},
             "url": "https://example.com/concerto"}
            </script></head><body></body></html>
            """
        )
        objs = list(ingest_jsonld._iter_jsonld_objects(html))
        self.assertEqual(len(objs), 1)
        self.assertTrue(ingest_jsonld._is_event(objs[0]))
        start = ingest_jsonld._parse_start("2026-07-15T21:00")
        self.assertEqual(start, (dt.date(2026, 7, 15), "21:00"))

    def test_filters_by_region_keyword(self):
        html = textwrap.dedent(
            """\
            <html><script type="application/ld+json">[
              {"@type":"Event","name":"Festa em São Miguel","startDate":"2026-08-01",
               "location":{"name":"Ponta Delgada"}},
              {"@type":"Event","name":"Festa em Terceira","startDate":"2026-08-02",
               "location":{"name":"Angra do Heroísmo"}}
            ]</script></html>
            """
        )
        from ingest_jsonld import JsonLdSource, harvest

        # Patch fetch to return our fixture instead of hitting the network.
        original_fetch = ingest_jsonld.fetch
        ingest_jsonld.fetch = lambda url: html  # type: ignore[assignment]
        try:
            events = harvest(JsonLdSource(slug="test.example", listing_url="https://x/y"))
        finally:
            ingest_jsonld.fetch = original_fetch
        names = [e["name"] for e in events]
        self.assertEqual(names, ["Festa em Terceira"])

    def test_handles_graph_wrapper(self):
        html = textwrap.dedent(
            """\
            <script type="application/ld+json">
            {"@context":"https://schema.org","@graph":[
              {"@type":"Event","name":"E1","startDate":"2026-09-01"},
              {"@type":"WebPage","name":"home"}
            ]}
            </script>
            """
        )
        objs = list(ingest_jsonld._iter_jsonld_objects(html))
        events = [o for o in objs if ingest_jsonld._is_event(o)]
        self.assertEqual(len(events), 1)


class TouradasParserTests(unittest.TestCase):
    def setUp(self):
        self.today = dt.date(2026, 1, 1)

    def test_long_form_date(self):
        text = "Tourada à corda no dia 15 de junho de 2026 com ganadeiro: ER"
        hits = ingest_touradas._candidate_dates(text, self.today)
        self.assertTrue(any(d == dt.date(2026, 6, 15) for d, _, _ in hits))

    def test_long_form_date_without_year_defaults_to_today_year(self):
        text = "Tourada à corda no dia 15 de junho"
        hits = ingest_touradas._candidate_dates(text, self.today)
        self.assertTrue(any(d == dt.date(self.today.year, 6, 15) for d, _, _ in hits))

    def test_numeric_date_pattern(self):
        text = "Bezerrada marcada para 07/06/2026 às 17h."
        hits = ingest_touradas._candidate_dates(text, self.today)
        self.assertTrue(any(d == dt.date(2026, 6, 7) for d, _, _ in hits))

    def test_past_dates_dropped(self):
        text = "Tourada à corda no dia 1 de janeiro de 2020."
        hits = ingest_touradas._candidate_dates(text, self.today)
        self.assertEqual(hits, [])

    def test_only_dates_near_tourada_keywords_are_kept(self):
        # The keyword check happens in harvest_junta on the windowed text;
        # _candidate_dates alone returns the date regardless. Verify the
        # keyword regex itself.
        self.assertIsNotNone(ingest_touradas.TOURADA_KEYWORDS_RE.search("Tourada à corda"))
        self.assertIsNone(ingest_touradas.TOURADA_KEYWORDS_RE.search("Concerto de jazz"))

    def test_ganadeiro_extraction(self):
        m = ingest_touradas.GANADEIRO_RE.search("Ganadeiro: Marcos Bastos")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).strip(), "Marcos Bastos")


if __name__ == "__main__":
    unittest.main()
