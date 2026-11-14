"""Year-less "Inauguração" labels become exhibition ranges when the description dates the opening.

The fixture holds the two What's On records as the public query returned them. Expected
dates and times are the ones those records print: the opening in the description, the end
of the run in ``datetime_end_date``, and the time in the description header.
"""
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
from ingest_common import format_event_yaml, listing_kind
from ingest_dates import MONTHS
from ingest_health import SourceError, SourceHealth

with open(os.path.join(os.path.dirname(__file__), "fixtures", "whatson", "inauguration_records.json"),
          encoding="utf-8") as handle:
    FIXTURE = json.load(handle)
CORES, PINTURA = FIXTURE["items"]
RELATED = FIXTURE["related"]
RUN_END = dt.date(2027, 1, 30)
MONTH_NAMES = {number: name for name, number in MONTHS.items()}


def described(record, label=None, header=None, extra=None, end=None):
    """Copy a fixture record, changing its label, the description's date header, an added paragraph or the CMS end date."""
    item = copy.deepcopy(record)
    if label is not None:
        item["text_display_date"] = {"all": label}
    text = item["text_description"]["all"]
    if header is not None:
        text = text.replace(text[text.index("<strong>") + 8:text.index("</strong>")], header, 1)
    if extra is not None:
        text += f"<p>{extra}</p>"
    item["text_description"] = {"all": text}
    if end is not None:
        item["datetime_end_date"] = end
    return item


class InaugurationRangeTests(unittest.TestCase):
    def test_fixture_labels_carry_no_year(self):
        self.assertEqual(CORES["text_display_date"]["all"], "Inauguração: 13 de novembro")
        self.assertEqual(PINTURA["text_display_date"]["all"], "Inauguração: 28 de novembro")
        self.assertEqual(CORES["datetime_end_date"][:10], "2027-01-30")
        self.assertEqual(PINTURA["datetime_end_date"][:10], "2027-01-30")

    def test_opening_with_printed_date_becomes_a_range_to_the_cms_end_date(self):
        events = portal.parse_record(CORES, RELATED)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["date"], dt.date(2026, 11, 13))
        self.assertEqual(event["end_date"], RUN_END)
        self.assertEqual(event["time"], "21:00")
        self.assertEqual(event["tags"], ["exhibition", "free"])
        self.assertEqual(event["source_uid"], "sxzsjkXxzeHQSAb6:2026-11-13@whatson.azores.gov.pt")

    def test_uncategorised_opening_is_still_an_exhibition(self):
        self.assertIsNone(PINTURA["ref_category"])
        event = portal.parse_record(PINTURA, RELATED)[0]
        self.assertEqual(event["date"], dt.date(2026, 11, 28))
        self.assertEqual(event["end_date"], RUN_END)
        self.assertEqual(event["time"], "15:00")
        self.assertEqual(event["tags"], ["exhibition", "free"])

    def test_category_tags_are_kept_and_no_exhibition_kind_is_forced(self):
        for title, tag in (("Música", "live-music"), ("Teatro", "theater")):
            related = {**RELATED, "other-category": {"_title": {"all": title}}}
            item = dict(PINTURA, ref_category="other-category")
            with self.subTest(category=title):
                event = portal.parse_record(item, related)[0]
                self.assertEqual((event["date"], event["end_date"]), (dt.date(2026, 11, 28), RUN_END))
                self.assertEqual(event["tags"], [tag, "free"])
                self.assertIsNone(listing_kind(event["tags"], event["date"], event["end_date"]))
                self.assertNotIn("kind:", format_event_yaml(event))

    def test_ranges_are_written_as_exhibition_listings(self):
        for record in (CORES, PINTURA):
            with self.subTest(record=record["id"]):
                event = portal.parse_record(record, RELATED)[0]
                self.assertEqual(listing_kind(event["tags"], event["date"], event["end_date"]), "exhibition")
                text = format_event_yaml(event)
                self.assertIn("  end_date: 2027-01-30\n", text)
                self.assertIn("  kind: exhibition\n", text)

    def test_both_records_are_discovered_without_review_errors(self):
        health = SourceHealth("test")
        with patch.object(portal, "fetch_records", return_value=(FIXTURE["items"], RELATED)):
            events = portal.discover_events(dt.date(2026, 11, 14), dt.date(2027, 3, 1), health)
        self.assertEqual([(event["name"], event["date"], event["end_date"]) for event in events], [
            ("Diversas são as Cores das Histórias", dt.date(2026, 11, 13), RUN_END),
            ("Exposição de Pintura de Vasco Pereira da Costa", dt.date(2026, 11, 28), RUN_END)])
        self.assertEqual((health.local, health.parsed, health.rejected), (2, 2, 0))

    def test_mismatch_without_an_inauguration_label_keeps_the_review_error(self):
        for label in ("13 de novembro", "Abertura: 13 de novembro", "Vernissage: 13 de novembro"):
            with self.subTest(label=label), self.assertRaisesRegex(SourceError, "year needs review"):
                portal.parse_record(described(CORES, label=label), RELATED)

    def test_label_that_is_more_than_an_inauguration_day_keeps_the_review_error(self):
        for label in ("Inauguração: 13 de novembro e 14 de novembro", "Inauguração: 13 de novembro | 21:00",
                      "Inauguração 13 de novembro às 21h00", "Reinauguração: 13 de novembro"):
            with self.subTest(label=label), self.assertRaises(SourceError):
                portal.parse_record(described(CORES, label=label), RELATED)

    def test_description_without_the_labelled_full_date_keeps_the_review_error(self):
        headers = {
            "no date at all": "Inauguração",
            "date without a year": "Inauguração: 13 de novembro",
            "another day": "Inauguração: 14 de novembro de 2026",
            "another month": "Inauguração: 13 de dezembro de 2026",
            "numeric date": "Inauguração: 13/11/2026",
        }
        for name, header in headers.items():
            with self.subTest(case=name), self.assertRaisesRegex(SourceError, "year needs review"):
                portal.parse_record(described(CORES, header=header), RELATED)

    def test_printed_year_after_the_cms_end_date_keeps_the_review_error(self):
        for header in ("Inauguração: 13 de novembro de 2027", "Inauguração: 13 de novembro de 2028"):
            with self.subTest(header=header), self.assertRaisesRegex(SourceError, "year needs review"):
                portal.parse_record(described(CORES, header=header), RELATED)

    def test_printed_opening_more_than_a_year_before_the_cms_end_date_keeps_the_review_error(self):
        item = described(CORES, header="Inauguração: 13 de novembro de 2025")
        self.assertEqual(item["datetime_end_date"][:10], "2027-01-30")
        with self.assertRaisesRegex(SourceError, "year needs review"):
            portal.parse_record(item, RELATED)

    def test_unrelated_earlier_date_with_the_same_day_and_month_keeps_the_review_error(self):
        item = described(CORES, header="Inauguração", extra="Inaugurada a 13 de novembro de 2019.")
        with self.assertRaisesRegex(SourceError, "year needs review"):
            portal.parse_record(item, RELATED)

    def test_run_length_bound_is_366_days(self):
        end = dt.date(2027, 1, 30)
        for days, expected in ((0, end), (365, end - dt.timedelta(days=365)), (366, end - dt.timedelta(days=366)),
                               (367, None), (444, None)):
            opening = end - dt.timedelta(days=days)
            description = f"<p>Inauguração: {opening.day} de {MONTH_NAMES[opening.month]} de {opening.year}</p>"
            label = f"Inauguração: {opening.day} de {MONTH_NAMES[opening.month]}"
            with self.subTest(days=days):
                self.assertEqual(portal.inauguration_opening(label, description, end), expected)

    def test_live_records_are_inside_the_run_length_bound(self):
        for record, opening in ((CORES, dt.date(2026, 11, 13)), (PINTURA, dt.date(2026, 11, 28))):
            with self.subTest(record=record["id"]):
                self.assertLessEqual((RUN_END - opening).days, portal.MAX_RUN_DAYS)
                self.assertEqual(portal.parse_record(record, RELATED)[0]["date"], opening)

    def test_cms_end_date_before_the_printed_opening_keeps_the_review_error(self):
        with self.assertRaisesRegex(SourceError, "year needs review"):
            portal.parse_record(described(CORES, end="2026-07-15T00:00:00Z"), RELATED)

    def test_contradicting_printed_years_keep_the_review_error(self):
        extras = {
            "earlier year, outside the run-length bound": "A 13 de novembro de 2025 abriu o atelier.",
            "later year, after the CMS end date": "Reabre a 13 de novembro de 2027.",
        }
        for case, extra in extras.items():
            with self.subTest(case=case), self.assertRaisesRegex(SourceError, "year needs review"):
                portal.parse_record(described(CORES, extra=extra), RELATED)

    def test_repeating_the_same_printed_date_is_not_a_contradiction(self):
        item = described(CORES, extra="Esperamos por si a 13 de novembro de 2026.")
        event = portal.parse_record(item, RELATED)[0]
        self.assertEqual((event["date"], event["end_date"]), (dt.date(2026, 11, 13), RUN_END))

    def test_other_printed_dates_do_not_affect_the_labelled_opening(self):
        item = described(CORES, extra="Encerra a 30 de janeiro de 2027.")
        event = portal.parse_record(item, RELATED)[0]
        self.assertEqual((event["date"], event["end_date"]), (dt.date(2026, 11, 13), RUN_END))

    def test_opening_on_the_last_day_of_the_run_is_a_single_day_event(self):
        event = portal.parse_record(described(PINTURA, end="2026-11-28T12:00:00Z"), RELATED)[0]
        self.assertEqual(event["date"], dt.date(2026, 11, 28))
        self.assertNotIn("end_date", event)
        self.assertEqual(event["tags"], ["free"])

    def test_invalid_calendar_day_ends_in_the_generic_day_out_of_range_error(self):
        item = described(PINTURA, label="Inauguração: 31 de novembro", header="Inauguração: 31 de novembro de 2026")
        self.assertIsNone(portal.inauguration_opening("Inauguração: 31 de novembro", item["text_description"]["all"],
                                                      RUN_END))
        with self.assertRaisesRegex(SourceError, r"day (?:is out of range for month|31 must be in range 1\.\.30)") as caught:
            portal.parse_record(item, RELATED)
        self.assertIsInstance(caught.exception.__cause__, ValueError)

    def test_session_day_errors_are_not_affected(self):
        item = described(CORES, label="Inauguração: 13 de novembro, 14 e 15 de dezembro")
        with self.assertRaisesRegex(SourceError, "Unconsumed session day"):
            portal.parse_record(item, RELATED)


if __name__ == "__main__":
    unittest.main()
