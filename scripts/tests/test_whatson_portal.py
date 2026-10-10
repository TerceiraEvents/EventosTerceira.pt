"""Fixtures for the public What’s On website query and displayed dates."""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
import ingest_whatson_azores as portal
from ingest_health import SourceError, SourceHealth

RELATED = {"island": {"_title": {"all": "Terceira"}},
           "other": {"_title": {"all": "São Miguel"}},
           "category": {"_title": {"all": "Música"}}}


def event_record():
    return {"id": "event", "_title": {"all": "Concerto de teste"},
            "_slug": {"all": "concerto"}, "ref_local": "island", "ref_category": "category",
            "text_venue": {"all": "Teatro Angrense"},
            "text_display_date": {"all": "30 de outubro de 2026"},
            "text_description": {"all": "<p>30 de outubro</p><p>21h30. Entrada livre.</p>"},
            "datetime_start_date": "2026-09-23T08:50:37.575Z",
            "datetime_end_date": "2026-10-30T00:00:00.000Z"}


class WhatsonPortalTests(unittest.TestCase):
    def test_uses_published_date_and_portuguese_venue(self):
        event = portal.parse_record(event_record(), RELATED)[0]
        self.assertEqual(event["date"], dt.date(2026, 10, 30))
        self.assertEqual(event["time"], "21:30")
        self.assertEqual(event["venue"], "Teatro Angrense")
        self.assertEqual(event["tags"], ["live-music", "free"])

    def test_three_discrete_concerts_have_distinct_dates_and_uids(self):
        item = event_record()
        item["text_display_date"] = {"all": "16 de janeiro, 13 de março e 17 de abril de 2027 | 21:00"}
        events = portal.parse_record(item, RELATED)
        self.assertEqual([event["date"] for event in events], [dt.date(2027, 1, 16), dt.date(2027, 3, 13), dt.date(2027, 4, 17)])
        self.assertEqual(len({event["source_uid"] for event in events}), 3)
        self.assertTrue(all("end_date" not in event for event in events))

    def test_end_only_listing_requires_a_verified_start(self):
        item = event_record()
        item["text_display_date"] = {"all": "Até 23 de novembro de 2026"}
        with self.assertRaises(SourceError):
            portal.parse_record(item, RELATED)
        known = [{"name": "Concerto de teste", "date": dt.date(2026, 8, 31)}]
        event = portal.parse_record(item, RELATED, known)[0]
        self.assertEqual(event["date"], dt.date(2026, 8, 31))
        self.assertEqual(event["end_date"], dt.date(2026, 11, 23))

    def test_island_filter_uses_reference_not_title_mentions(self):
        local = event_record()
        other = copy.deepcopy(local)
        other.update(id="other-event", ref_local="other", _title={"all": "Artista da Terceira em São Miguel"})
        health = SourceHealth("test")
        with patch.object(portal, "fetch_records", return_value=([local, other], RELATED)):
            result = portal.discover_events(dt.date(2026, 10, 1), dt.date(2027, 1, 1), health)
        self.assertEqual(len(result), 1)
        self.assertEqual(health.local, 1)

    def test_all_pages_are_fetched(self):
        health = SourceHealth("test")
        structure = {"hash": 123, "repeaters": {portal.REPEATER_ID: {"pagination": {"enabled": True}}}}
        a, b = event_record(), event_record()
        b["id"] = "second"
        responses = [b"window.BndLyrStruct = " + json.dumps(structure).encode() + b";",
                     json.dumps({"page": 1, "totalPages": 2, "items": [a], "related": RELATED}).encode(),
                     json.dumps({"page": 2, "totalPages": 2, "items": [b], "related": RELATED}).encode()]
        with patch.object(health, "fetch", side_effect=responses) as fetch:
            items, related = portal.fetch_records(health)
            self.assertEqual([item["id"] for item in items], ["event", "second"])
            self.assertEqual(fetch.call_args_list[2].args[1]["repeater"]["page"], 2)
        self.assertEqual(health.listed, 2)
        self.assertEqual(related, RELATED)

    def test_invalid_empty_repeated_and_truncated_pages_fail(self):
        structure = {"hash": 123, "repeaters": {portal.REPEATER_ID: {"pagination": {"enabled": True}}}}
        cases = [
            {"page": 1, "totalPages": 1, "items": []},
            {"page": 2, "totalPages": 1, "items": [event_record()]},
            {"page": 1, "totalPages": 999, "items": [event_record()]},
            {"page": 1, "totalPages": 1, "items": [event_record(), event_record()]},
            {"error": "forbidden"},
        ]
        for response in cases:
            with self.subTest(response=response), patch.object(SourceHealth, "fetch", side_effect=[
                b"window.BndLyrStruct = " + json.dumps(structure).encode() + b";", json.dumps(response).encode()
            ]), self.assertRaises(SourceError):
                portal.fetch_records(SourceHealth("test"))

    def test_recognized_empty_source_succeeds(self):
        health = SourceHealth("test")
        with patch.object(portal, "fetch_records", return_value=([], {})):
            self.assertEqual(portal.discover_events(dt.date(2026, 10, 1), dt.date(2027, 1, 1), health), [])

    def test_incomplete_local_record_fails_instead_of_disappearing(self):
        item = event_record()
        item["text_display_date"] = {"all": "em breve"}
        with patch.object(portal, "fetch_records", return_value=([item], RELATED)), self.assertRaises(SourceError):
            portal.discover_events(dt.date(2026, 10, 1), dt.date(2027, 1, 1), SourceHealth("test"))

    def test_missing_or_unknown_island_reference_fails(self):
        for value in (None, "unknown"):
            item = event_record()
            item["ref_local"] = value
            with self.subTest(value=value), patch.object(portal, "fetch_records", return_value=([item], RELATED)), self.assertRaises(SourceError):
                portal.discover_events(dt.date(2026, 10, 1), dt.date(2027, 1, 1), SourceHealth("test"))

    def test_stale_cms_year_is_flagged(self):
        item = event_record()
        item["text_display_date"] = {"all": "30 de outubro"}
        item["datetime_end_date"] = "2026-07-15T00:00:00Z"
        with self.assertRaises(SourceError):
            portal.parse_record(item, RELATED)


if __name__ == "__main__":
    unittest.main()
