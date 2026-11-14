"""Tests for the shared event-name matcher used to deduplicate ingested events.

Run from the repo root:

    python -m unittest scripts.tests.test_name_matcher -v
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

from ingest_common import is_similar_match, matches_existing


class NameMatcherTests(unittest.TestCase):
    def test_short_title_matches_the_same_title_behind_a_category_label(self):
        cases = (
            ("ROMANCE À ITALIANA", "Cinema: Romance à Italiana"),
            ("STREET FIGHTER", "Cinema: Street Fighter"),
            ("A ILHA ESQUECIDA", "Cinema: A Ilha Esquecida"),
            ("Aurora", "Concerto: Aurora"),
        )
        for bare, labelled in cases:
            with self.subTest(bare=bare, labelled=labelled):
                self.assertTrue(is_similar_match(bare, labelled))
                self.assertTrue(is_similar_match(labelled, bare))

    def test_different_short_titles_do_not_match(self):
        cases = (
            ("CLAYFACE", "Cinema: Street Fighter"),
            ("Cinema: Verity", "Cinema: Clayface"),
            ("Romance", "Cinema: Romance à Italiana"),
        )
        for first, second in cases:
            with self.subTest(first=first, second=second):
                self.assertFalse(is_similar_match(first, second))

    def test_unrelated_labels_and_conflicting_labels_are_not_stripped(self):
        self.assertFalse(is_similar_match("Aurora", "Escama: Aurora"))
        self.assertFalse(is_similar_match("Concerto: Aurora", "Cinema: Aurora"))

    def test_long_name_rules_are_unchanged(self):
        self.assertTrue(is_similar_match(
            "Concerto: Notas em Movimento",
            "Concerto: Notas em Movimento - quando a tradição encontra a energia académica"))
        self.assertFalse(is_similar_match("Cinema: Verity", "Concerto de Natal"))

    def test_matches_existing_requires_the_same_date(self):
        day = dt.date(2026, 11, 26)
        index = {day: ["Cinema: Romance à Italiana"]}
        self.assertTrue(matches_existing("ROMANCE À ITALIANA", day, index))
        self.assertFalse(matches_existing("ROMANCE À ITALIANA", dt.date(2026, 11, 27), index))



if __name__ == "__main__":
    unittest.main()
