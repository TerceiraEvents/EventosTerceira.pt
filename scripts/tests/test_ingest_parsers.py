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

import contextlib
import datetime as dt
import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

# Allow `from ingest_* import ...` whether run from repo root or from
# scripts/tests/ directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

import icalendar
import ingest_cmah
import ingest_jsonld
import ingest_touradas
import yaml
from ingest_common import format_event_yaml, listing_kind


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


def vevent(dtstart: str, dtend: str | None = None, summary: str = "Evento", extra: str = "") -> icalendar.Event:
    """Build a CMAH-style VEVENT; the property lines are copied from the live feed's forms."""
    lines = ["BEGIN:VEVENT", "UID:1@angradoheroismo.pt", dtstart]
    if dtend:
        lines.append(dtend)
    lines += [f"SUMMARY:{summary}", "LOCATION:Venue\\, Street\\, Angra do Heroísmo", extra, "END:VEVENT"]
    return icalendar.Event.from_ical("\r\n".join(line for line in lines if line))


ALL_DAY = "{name};TZID=Atlantic/Azores;VALUE=DATE:{day}"
TIMED = "{name};TZID=Atlantic/Azores:{day}T{clock}"


class CmahDatesTests(unittest.TestCase):
    def dates(self, dtstart: str, dtend: str | None):
        component = vevent(dtstart, dtend)
        start = component.get("DTSTART")
        end = component.get("DTEND")
        date, time = ingest_cmah.extract_date_time(start)
        return date, time, ingest_cmah.extract_end_date(start, end)

    def test_all_day_end_is_exclusive(self):
        cases = (
            ("20261120", "20270111", dt.date(2027, 1, 10)),
            ("20261120", "20261122", dt.date(2026, 11, 21)),
            ("20261120", "20261121", None),
        )
        for first, last, expected in cases:
            with self.subTest(first=first, last=last):
                date, time, end = self.dates(ALL_DAY.format(name="DTSTART", day=first),
                                             ALL_DAY.format(name="DTEND", day=last))
                self.assertEqual((date, time, end), (dt.date.fromisoformat(first[:4] + "-" + first[4:6] + "-" + first[6:]), None, expected))

    def test_timed_multi_day_end_is_the_end_date(self):
        cases = (
            ((("20261113", "190000"), ("20261114", "190000")), ("19:00", dt.date(2026, 11, 14))),
            ((("20261113", "200000"), ("20261115", "223000")), ("20:00", dt.date(2026, 11, 15))),
            ((("20261127", "160000"), ("20261128", "220000")), ("16:00", dt.date(2026, 11, 28))),
            ((("20261122", "160000"), ("20261204", "183000")), ("16:00", dt.date(2026, 12, 4))),
            ((("20261121", "190000"), ("20261122", "184500")), ("19:00", dt.date(2026, 11, 22))),
            ((("20261121", "230000"), ("20261122", "061500")), ("23:00", dt.date(2026, 11, 22))),
        )
        for ((first, start_clock), (last, end_clock)), (time, end_date) in cases:
            with self.subTest(first=first, last=last):
                _, got_time, got_end = self.dates(TIMED.format(name="DTSTART", day=first, clock=start_clock),
                                                  TIMED.format(name="DTEND", day=last, clock=end_clock))
                self.assertEqual((got_time, got_end), (time, end_date))

    def test_midnight_start_has_no_time_and_keeps_the_end_date(self):
        _, time, end = self.dates(TIMED.format(name="DTSTART", day="20261118", clock="000000"),
                                  TIMED.format(name="DTEND", day="20261122", clock="000000"))
        self.assertIsNone(time)
        self.assertEqual(end, dt.date(2026, 11, 22))

    def test_overnight_finish_is_not_a_second_day(self):
        cases = (("220000", "020000"), ("210000", "000000"), ("233000", "060000"))
        for start_clock, end_clock in cases:
            with self.subTest(start=start_clock, end=end_clock):
                _, time, end = self.dates(TIMED.format(name="DTSTART", day="20261121", clock=start_clock),
                                          TIMED.format(name="DTEND", day="20261122", clock=end_clock))
                self.assertEqual(time, f"{start_clock[:2]}:{start_clock[2:4]}")
                self.assertIsNone(end)

    def test_same_day_missing_and_reversed_ends_give_no_end_date(self):
        start = TIMED.format(name="DTSTART", day="20261121", clock="210000")
        cases = (
            TIMED.format(name="DTEND", day="20261121", clock="230000"),
            TIMED.format(name="DTEND", day="20261120", clock="230000"),
            None,
        )
        for dtend in cases:
            with self.subTest(dtend=dtend):
                self.assertIsNone(self.dates(start, dtend)[2])

    def test_main_writes_end_date_and_omits_midnight_time(self):
        calendar = textwrap.dedent(
            """\
            BEGIN:VCALENDAR
            VERSION:2.0
            BEGIN:VEVENT
            UID:5001@angradoheroismo.pt
            DTSTART;TZID=Atlantic/Azores:20990518T000000
            DTEND;TZID=Atlantic/Azores:20990522T000000
            SUMMARY:Festival de teste em Angra
            LOCATION:Venue\\, Street\\, Angra do Heroísmo
            CATEGORIES:Exposições
            END:VEVENT
            BEGIN:VEVENT
            UID:5002@angradoheroismo.pt
            DTSTART;TZID=Atlantic/Azores:20990521T220000
            DTEND;TZID=Atlantic/Azores:20990522T020000
            SUMMARY:Concerto de teste noturno
            LOCATION:Venue\\, Street\\, Angra do Heroísmo
            END:VEVENT
            END:VCALENDAR
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            ics, store = Path(tmp) / "events.ics", Path(tmp) / "events.yml"
            ics.write_text(calendar, encoding="utf-8")
            store.write_text("[]\n", encoding="utf-8")
            argv = ["ingest_cmah", "--dry-run", "--url", ics.as_uri(), "--yaml-path", str(store)]
            output = io.StringIO()
            with patch.object(sys, "argv", argv), patch.object(ingest_cmah, "LOOKAHEAD_DAYS", 40000), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(ingest_cmah.main(), 0)
        events = {event["source_uid"]: event for event in yaml.safe_load(output.getvalue())}
        festival, concert = events["5001@angradoheroismo.pt"], events["5002@angradoheroismo.pt"]
        self.assertEqual((festival["date"], festival["end_date"]), (dt.date(2099, 5, 18), dt.date(2099, 5, 22)))
        self.assertNotIn("time", festival)
        self.assertEqual(festival["kind"], "exhibition")
        self.assertEqual(concert["time"], "22:00")
        self.assertNotIn("end_date", concert)


class ListingKindTests(unittest.TestCase):
    def test_classifies_only_multi_day_exhibition_tagged_records(self):
        cases = (
            (["exhibition"], dt.date(2026, 10, 1), dt.date(2026, 10, 2), "exhibition"),
            (["exhibition"], dt.date(2026, 10, 1), dt.date(2026, 10, 1), None),
            (["exhibition"], dt.date(2026, 10, 1), None, None),
            (["live-music"], dt.date(2026, 10, 1), dt.date(2026, 10, 2), None),
            (["festival"], dt.date(2026, 10, 1), dt.date(2026, 10, 2), None),
        )
        for tags, start, end, expected in cases:
            with self.subTest(tags=tags, start=start, end=end):
                self.assertEqual(listing_kind(tags, start, end), expected)

    def test_non_exhibition_ranges_do_not_write_a_kind_key(self):
        cases = (
            {"date": dt.date(2026, 10, 1), "name": "Single day", "venue": "Venue",
             "tags": ["exhibition"]},
            {"date": dt.date(2026, 10, 1), "end_date": dt.date(2026, 10, 2),
             "name": "Festival", "venue": "Venue", "tags": ["festival"]},
        )
        for event in cases:
            with self.subTest(event=event):
                self.assertNotIn("  kind:", format_event_yaml(event))


if __name__ == "__main__":
    unittest.main()
