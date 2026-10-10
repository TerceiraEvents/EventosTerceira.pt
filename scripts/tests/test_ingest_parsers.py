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
import ingest_touradas


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
