"""Every event publishes its title and description in English and Portuguese.

A bare `name` / `description` is English when a `_pt` sibling exists and
Portuguese when an `_en` sibling exists, so an event is bilingual when it
carries at least one explicit sibling next to the bare field, or both
explicit siblings. Events with no description at all are skipped.
"""
import os
import unittest

import yaml

ROOT = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
EVENTS = os.path.join(ROOT, "_data", "special_events.yml")


def text(event, key):
    value = event.get(key)
    return value.strip() if isinstance(value, str) else ""


def missing_locales(event, field):
    bare, en, pt = text(event, field), text(event, field + "_en"), text(event, field + "_pt")
    if not (bare or en or pt):
        return []
    missing = []
    if not (en or (bare and pt)):
        missing.append("en")
    if not (pt or (bare and en)):
        missing.append("pt")
    return missing


def audit(events):
    gaps = []
    for event in events:
        for field in ("name", "description"):
            for locale in missing_locales(event, field):
                gaps.append("%s: %s (%s) lacks %s" % (event.get("id"), event.get("name"), field, locale))
    return gaps


class EventLocaleTests(unittest.TestCase):
    def test_audit_detects_gaps(self):
        self.assertEqual(missing_locales({"name": "A"}, "name"), ["en", "pt"])
        self.assertEqual(missing_locales({"name": "A", "name_pt": "B"}, "name"), [])
        self.assertEqual(missing_locales({"name": "A", "name_en": "B"}, "name"), [])
        self.assertEqual(missing_locales({"description_pt": "B"}, "description"), ["en"])
        self.assertEqual(missing_locales({"description_pt": "B", "description_en": "C"}, "description"), [])
        self.assertEqual(missing_locales({"name": "A", "name_pt": " "}, "name"), ["en", "pt"])
        self.assertEqual(missing_locales({}, "description"), [])

    def test_every_event_has_both_locales(self):
        with open(EVENTS, encoding="utf-8") as handle:
            events = yaml.safe_load(handle)
        gaps = audit(events)
        self.assertEqual(gaps, [], "%d locale gaps:\n%s" % (len(gaps), "\n".join(gaps[:50])))


if __name__ == "__main__":
    unittest.main()
