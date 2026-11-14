"""Stored CMAH entries carry the date range their iCal record publishes.

`fixtures/cmah/multiday_entries.ics` holds two VEVENTs copied from the live
feed (UID, DTSTART, DTEND, SUMMARY). Their stored entries were appended
before the ingester read DTEND, so they were published as single days. Each
stored entry must agree with what the ingester derives from its iCal record.
"""

from __future__ import annotations

import datetime as dt
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

import icalendar
import ingest_cmah
import yaml
from ingest_common import listing_kind

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "_data" / "special_events.yml"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cmah" / "multiday_entries.ics"

# Last day and listing kind each record publishes. 1937: DTEND is
# 2027-01-31T20:00 and its description says "entre os dias 29 e 31 de
# janeiro". 2010: DTEND is 2026-12-31T19:00 and its description says "decorre
# durante o mês de novembro e dezembro de 2026".
EXPECTED = {
    "1937@angradoheroismo.pt": (dt.date(2027, 1, 31), None),
    "2010@angradoheroismo.pt": (dt.date(2026, 12, 31), "exhibition"),
}


class CmahStoredRangesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with EVENTS.open(encoding="utf-8") as handle:
            cls.stored = {event.get("source_uid"): event for event in yaml.safe_load(handle)}
        cls.feed = {
            str(component.get("UID")): component
            for component in icalendar.Calendar.from_ical(FIXTURE.read_bytes()).walk("VEVENT")
        }

    def test_fixture_covers_every_expected_uid(self):
        self.assertEqual(set(self.feed), set(EXPECTED))

    def test_ingester_reads_the_published_range(self):
        for uid, (end_date, _kind) in EXPECTED.items():
            with self.subTest(uid=uid):
                component = self.feed[uid]
                start, end = component.get("DTSTART"), component.get("DTEND")
                self.assertEqual(ingest_cmah.extract_end_date(start, end), end_date)

    def test_stored_entries_match_the_ingester(self):
        for uid, (end_date, kind) in EXPECTED.items():
            with self.subTest(uid=uid):
                entry = self.stored[uid]
                date, time = ingest_cmah.extract_date_time(self.feed[uid].get("DTSTART"))
                self.assertEqual(entry["date"], date)
                self.assertEqual(entry.get("time"), time)
                self.assertEqual(entry.get("end_date"), end_date)
                self.assertEqual(entry.get("kind"), kind)
                self.assertEqual(listing_kind(entry.get("tags"), entry["date"], end_date), kind)


if __name__ == "__main__":
    unittest.main()
