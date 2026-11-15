"""Cross-source duplicates: the same event listed by two calendars.

An ingest candidate with the same title and start time as a stored event on
the same day is a duplicate whatever the venue string says; titles that only
overlap (another language, a series label) must also agree on the venue. Two
different known localities at the same minute are a loud review error.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

import ingest_common as common
import ingest_health as health
import yaml
from ingest_health import SourceError, _duplicate, _venue_key, run_ingester

AJAIT = "Academia da Juventude e das Artes da Ilha Terceira (AJAIT)"
CCCAH = "Centro Cultural e de Congressos de Angra do Heroísmo"
TICKETLINE_CCCAH = "C.C.C. Angra Do Heroísmo - Pequeno Auditório"
WHATSON = "@whatson.azores.gov.pt"


def event(name, day, time, venue, **fields):
    return {"name": name, "date": dt.date.fromisoformat(day), "time": time, "venue": venue, **fields}


# (stored record, ingest candidate): two calendars listing one real event.
# The records are copied from _data/special_events.yml; the candidates are
# what the What's On, Ticketline and CMPV ingesters produced.
ISSUE_326_PAIRS = {
    "same title, venue string differs": (
        event("Obra Reunida de Álvaro Monjardino", "2026-11-15", "18:00", AJAIT, locality="praia"),
        event("Obra Reunida de Álvaro Monjardino", "2026-11-15", "18:00", "Bar da Academia de Juventude e das Artes",
              source_uid="sVwZBHqm8mWRan51:2026-11-15" + WHATSON),
    ),
    "capitalisation differs, venue string differs": (
        event("Património Cultural dos Açores: reflexões para uma estratégia integrada", "2026-11-15", "16:30", AJAIT,
              locality="praia"),
        event("Património Cultural dos Açores: Reflexões para uma estratégia integrada", "2026-11-15", "16:30",
              "Bar da Academia de Juventude e das Artes", source_uid="sbmD1ehsyXLfQwQd:2026-11-15" + WHATSON),
    ),
    "other language, locality suffix on the venue": (
        event("Cinema: Ocean with David Attenborough", "2026-11-16", "20:00", "Auditório do Ramo Grande",
              name_en="Film: Ocean with David Attenborough", locality="praia", source_uid="cmpv-916-2026-11-16"),
        event("“Ocean” com David Attenborough regressa à ilha Terceira", "2026-11-16", "20:00",
              "Auditório do Ramo Grande, Praia da Vitória", source_uid="srclertMzIawR8FI:2026-11-16" + WHATSON),
    ),
    "series label dropped, venue variant": (
        event("Mesa redonda: Para Lá das Colunas de Hércules", "2026-11-15", "20:00", AJAIT, locality="praia"),
        event("Para lá das Colunas de Hércules: a descoberta dos Açores e a primeira globalização", "2026-11-15",
              "20:00", "Bar da Academia de Juventude e das Artes da Ilha Terceira",
              source_uid="sdpq0jM9U9wI5pEV:2026-11-15" + WHATSON),
    ),
    "same title, venue named with a building": (
        event("Azores GameFest 2027", "2027-01-29", "10:00", "Parque Multissetorial da Ilha Terceira",
              end_date=dt.date(2027, 1, 31)),
        event("Azores GameFest 2027", "2027-01-29", "10:00",
              "Pavilhão Multiusos do Parque Multissetorial da Ilha Terceira",
              source_uid="s3d9xGameFest:2027-01-29" + WHATSON),
    ),
}

# A published run and the single-day Ticketline listing of its first night.
CINEMA_PAIRS = {
    title: (
        event(f"Cinema: {title}", start, "21:00", CCCAH, end_date=dt.date.fromisoformat(end), locality="angra"),
        event(title.upper(), start, "21:00", TICKETLINE_CCCAH, source_uid=f"{uid}@ticketline.pt"),
    )
    for title, start, end, uid in (
        ("O Veredito Social", "2026-11-05", "2026-11-09", "108929"),
        ("Street Fighter", "2026-11-12", "2026-11-16", "108930"),
        ("A Ilha Esquecida", "2026-11-14", "2026-11-15", "108934"),
        ("Clayface", "2026-11-19", "2026-11-23", "108939"),
    )
}

# Already matched on main; kept as a regression fixture.
COMEDIA_PAIR = (
    event("Workshop: Comédia de Improviso", "2026-11-14", "15:00–18:00",
          "Edifício Cultural de São Bento — Sala da Academia de Artes"),
    event("Comédia de Improviso", "2026-11-14", "15:00", "Edifício Cultural de S. Bento",
          source_uid="sAxJXAELv3h3619i:2026-11-14" + WHATSON),
)


class DuplicatePairTests(unittest.TestCase):
    def assertDuplicateBothWays(self, stored, candidate):
        self.assertTrue(_duplicate(candidate, [stored]), "candidate should match the stored event")
        self.assertTrue(_duplicate(stored, [candidate]), "stored event should match the candidate")

    def test_issue_326_pairs_are_duplicates(self):
        for label, (stored, candidate) in ISSUE_326_PAIRS.items():
            with self.subTest(label):
                self.assertDuplicateBothWays(stored, candidate)

    def test_published_runs_match_their_ticketline_listing(self):
        for title, (stored, candidate) in CINEMA_PAIRS.items():
            with self.subTest(title):
                self.assertDuplicateBothWays(stored, candidate)

    def test_comedia_de_improviso_still_matches(self):
        self.assertDuplicateBothWays(*COMEDIA_PAIR)



class NotDuplicateTests(unittest.TestCase):
    def setUp(self):
        self.stored = event("Obra Reunida de Álvaro Monjardino", "2026-11-15", "18:00", AJAIT, locality="praia")
        self.candidate = event("Obra Reunida de Álvaro Monjardino", "2026-11-15", "18:00",
                               "Bar da Academia de Juventude e das Artes")

    def test_the_fixture_pair_is_a_duplicate(self):
        self.assertTrue(_duplicate(self.candidate, [self.stored]))

    def test_other_day_is_not_a_duplicate(self):
        self.assertFalse(_duplicate(dict(self.candidate, date=dt.date(2026, 11, 22)), [self.stored]))

    def test_other_start_time_at_another_venue_is_not_a_duplicate(self):
        candidate = dict(self.candidate, time="20:30", venue="Teatro Angrense")
        self.assertFalse(_duplicate(candidate, [self.stored]))

    def test_missing_start_time_does_not_trigger_the_title_rule(self):
        candidate = dict(self.candidate, time=None, venue="Teatro Angrense")
        self.assertFalse(_duplicate(candidate, [self.stored]))

    def test_different_titles_at_the_same_minute_are_not_duplicates(self):
        candidate = dict(self.candidate, name="Lançamento da revista Atlântida")
        self.assertFalse(_duplicate(candidate, [self.stored]))
        candidate = dict(self.candidate, name="Obra Completa de Álvaro Cunhal", venue=AJAIT)
        self.assertFalse(_duplicate(candidate, [self.stored]))

    def test_different_event_type_labels_are_different_titles(self):
        stored = event("Concerto: Fado Vivo", "2026-12-05", "21:00", "Teatro Angrense")
        candidate = event("Cinema: Fado Vivo", "2026-12-05", "21:00", "Auditório do Ramo Grande")
        self.assertFalse(_duplicate(candidate, [stored]))
        self.assertFalse(_duplicate(dict(candidate, venue="Teatro Angrense"), [stored]))

    def test_overlapping_titles_need_the_same_venue(self):
        stored, candidate = ISSUE_326_PAIRS["other language, locality suffix on the venue"]
        self.assertFalse(_duplicate(dict(candidate, venue="Teatro Angrense"), [stored]))

    def test_overlapping_titles_need_three_shared_words(self):
        stored = event("Noite de Fado", "2026-12-05", "21:00", "Teatro Angrense")
        candidate = event("Noite de Fado no Teatro", "2026-12-05", "21:00", "Teatro Angrense")
        self.assertFalse(common.is_contained_title(stored["name"], candidate["name"]))
        self.assertTrue(common.is_contained_title("Noite de Fado em Angra", "Noite de Fado em Angra do Heroísmo"))

    def test_series_label_is_only_dropped_for_the_contained_words(self):
        self.assertFalse(common.is_contained_title("Mesa redonda: Colunas de Hércules", "Colunas de Hércules"))
        self.assertTrue(common.is_contained_title("Mesa redonda: Para Lá das Colunas de Hércules",
                                                  "Para lá das Colunas de Hércules: a descoberta dos Açores"))


class TranslatedSiblingTests(unittest.TestCase):
    """A record stores its title in the source language and the translation in a sibling."""

    PT = event("Mercado de Natal em Angra", "2026-12-20", "18:00", "Praça Velha")
    EN = event("Christmas Market in Angra", "2026-12-20", "18:00", "Praça Velha")

    def stored(self, bare, sibling_key, sibling):
        return {**bare, sibling_key: sibling}

    def test_pt_candidate_matches_visit_azores_record_with_name_pt(self):
        stored = self.stored(self.EN, "name_pt", self.PT["name"])
        self.assertTrue(_duplicate(dict(self.PT), [stored]))
        self.assertTrue(common.same_instant(dict(self.PT), stored))

    def test_en_candidate_matches_portuguese_record_with_name_en(self):
        stored = self.stored(self.PT, "name_en", self.EN["name"])
        self.assertTrue(_duplicate(dict(self.EN), [stored]))
        self.assertTrue(common.same_instant(dict(self.EN), stored))

    def test_dedup_index_holds_every_title_of_a_record(self):
        for key, bare, other in (("name_pt", self.EN, self.PT), ("name_en", self.PT, self.EN)):
            with self.subTest(key=key):
                stored = self.stored(bare, key, other["name"])
                names, _ = common.build_dedup_index([stored])
                candidate = other["name"]
                self.assertTrue(common.matches_existing(candidate, bare["date"], names))

    def test_unrelated_sibling_is_not_a_duplicate(self):
        stored = self.stored(self.PT, "name_en", "Boat trip to Graciosa")
        self.assertFalse(_duplicate(event("Concerto de Jazz", "2026-12-20", "21:00", "Teatro Angrense"),
                                    [stored]))


class LocalityConflictTests(unittest.TestCase):
    def setUp(self):
        self.stored = event("Concerto de Natal", "2026-12-12", "21:00", "Teatro Angrense", locality="angra")
        self.candidate = event("Concerto de Natal", "2026-12-12", "21:00", "Auditório do Ramo Grande",
                               locality="praia")

    def test_same_title_and_minute_in_two_localities_raises_the_review_error(self):
        with self.assertRaisesRegex(health.VenueConflict, "different locality"):
            _duplicate(self.candidate, [self.stored])
        self.assertTrue(issubclass(health.VenueConflict, SourceError))

    def test_an_unknown_locality_is_a_silent_duplicate(self):
        self.assertTrue(_duplicate(dict(self.candidate, locality=None, venue="Salão Paroquial"), [self.stored]))

    def test_the_same_locality_is_a_silent_duplicate(self):
        self.assertTrue(_duplicate(dict(self.candidate, locality="angra"), [self.stored]))

    def test_agreeing_venues_never_raise(self):
        self.assertTrue(_duplicate(dict(self.stored), [dict(self.stored, source_uid="x")]))

    def test_a_matching_record_wins_over_a_conflicting_one(self):
        parallel = dict(self.stored, venue="Auditório do Ramo Grande", locality="praia", source_url="u/praia")
        angra = dict(self.stored, source_url="u/angra")
        candidate = dict(self.stored, source_url="u/new")
        for stored in ([parallel, angra], [angra, parallel]):
            with self.subTest(order=[record["locality"] for record in stored]):
                self.assertIs(health._find_duplicate(candidate, stored), angra)
                self.assertTrue(_duplicate(candidate, stored))
        with self.assertRaises(health.VenueConflict):
            health._find_duplicate(dict(candidate, venue="Salão Paroquial do Porto Martins", locality="other"),
                            [parallel, angra])

    def test_the_error_stops_the_run_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, report = Path(tmp) / "events.yml", Path(tmp) / "health.json"
            path.write_text(yaml.safe_dump([dict(self.stored, source_url="https://example.test/a")],
                                           allow_unicode=True), encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            candidate = dict(self.candidate, source_url="https://example.test/b")
            with patch.object(sys, "argv", ["test", "--yaml-path", str(path), "--health-report", str(report),
                                           "--today", "2026-12-01"]):
                self.assertEqual(run_ingester("fixture", lambda *args: [candidate]), 1)
            self.assertEqual(path.read_text(encoding="utf-8"), before)
            summary = json.loads(report.read_text())
            self.assertEqual(summary["status"], "degraded")
            self.assertIn("different locality", summary["errors"][0])


class RunIngesterTests(unittest.TestCase):
    def test_the_issue_326_pairs_are_skipped_and_a_new_event_is_kept(self):
        stored = [dict(pair[0], source_url=f"https://example.test/stored/{index}")
                  for index, pair in enumerate(ISSUE_326_PAIRS.values())]
        candidates = [dict(pair[1], source_url=f"https://example.test/candidate/{index}")
                      for index, pair in enumerate(ISSUE_326_PAIRS.values())]
        new = event("Domingos com Música", "2026-11-22", "11:00", "Igreja de Nossa Senhora da Guia",
                    source_url="https://example.test/new")
        with tempfile.TemporaryDirectory() as tmp:
            path, report = Path(tmp) / "events.yml", Path(tmp) / "health.json"
            path.write_text(yaml.safe_dump(stored, allow_unicode=True), encoding="utf-8")
            with patch.object(sys, "argv", ["test", "--yaml-path", str(path), "--health-report", str(report),
                                           "--today", "2026-11-14", "--lookahead-days", "400"]):
                self.assertEqual(run_ingester("fixture", lambda *args: candidates + [new]), 0)
            summary = json.loads(report.read_text())
            self.assertEqual((summary["duplicates"], summary["candidates"], summary["added"]),
                             (len(ISSUE_326_PAIRS), 1, 1))
            self.assertEqual(len(yaml.safe_load(path.read_text())), len(stored) + 1)


class InRunTests(unittest.TestCase):
    def test_two_candidates_of_one_run_are_deduplicated_against_each_other(self):
        first = event("Obra Reunida de Álvaro Monjardino", "2026-11-15", "18:00", AJAIT,
                      source_url="https://example.test/a")
        second = dict(first, venue="Bar da Academia de Juventude e das Artes", source_url="https://example.test/b")
        with tempfile.TemporaryDirectory() as tmp:
            path, report = Path(tmp) / "events.yml", Path(tmp) / "health.json"
            path.write_text("[]\n", encoding="utf-8")
            with patch.object(sys, "argv", ["test", "--yaml-path", str(path), "--health-report", str(report),
                                           "--today", "2026-11-14"]):
                self.assertEqual(run_ingester("fixture", lambda *args: [first, second]), 0)
            summary = json.loads(report.read_text())
            self.assertEqual((summary["duplicates"], summary["added"]), (1, 1))


class NormalisationTests(unittest.TestCase):
    def test_same_title_ignores_case_accents_quotes_dashes_and_punctuation(self):
        cases = (
            ("OBRA REUNIDA DE ALVARO MONJARDINO", "Obra Reunida de Álvaro Monjardino"),
            ("“Ocean” com David Attenborough", "Ocean com David Attenborough"),
            ("Dança – Noite de Fado!", "Danca - noite de fado"),
            ("Tertúlia: Paleográfica", "Tertulia Paleografica"),
        )
        for first, second in cases:
            with self.subTest(first=first):
                self.assertTrue(common.same_title(first, second))
                self.assertTrue(common.is_similar_match(first, second))

    def test_same_title_keeps_words_and_event_type_labels_apart(self):
        cases = (
            ("Obra Reunida", "Obra Completa"),
            ("Concerto: Aurora", "Cinema: Aurora"),
            ("!!!", "???"),
        )
        for first, second in cases:
            with self.subTest(first=first):
                self.assertFalse(common.same_title(first, second))

    def test_start_time_reads_the_first_clock_of_a_time_field(self):
        cases = (("15:00", "15:00"), ("15:00–18:00", "15:00"), ("9:30", "09:30"), ("21h30", "21:30"),
                 ("", None), (None, None), ("noite", None))
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(common.start_time(value), expected)

    def test_ajait_venue_variants_share_a_key(self):
        variants = (AJAIT, "Bar da Academia de Juventude e das Artes", "Academia de Juventude e das Artes da Ilha Terceira",
                    "Bar da Academia de Juventude e das Artes da Ilha Terceira")
        self.assertEqual({_venue_key(variant) for variant in variants}, {"ajait"})
        self.assertNotEqual(_venue_key("Auditório do Ramo Grande"), "ajait")

    def test_venue_locality_uses_the_record_then_the_alias_file(self):
        aliases = textwrap.dedent(
            """\
            - key: ramo-grande
              locality: praia
              aliases: [Auditório do Ramo Grande]
            - key: cccah
              locality: angra
              aliases: [Centro Cultural e de Congressos de Angra do Heroísmo]
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "venue_localities.yml"
            path.write_text(aliases, encoding="utf-8")
            with patch.object(common, "VENUE_LOCALITIES_PATH", path):
                self.assertEqual(common.venue_locality("Auditório do Ramo Grande, Praia da Vitória"), "praia")
                self.assertEqual(common.venue_locality("Auditório do Ramo Grande", "angra"), "angra")
                self.assertIsNone(common.venue_locality("Bar da Academia de Juventude e das Artes"))
                self.assertIsNone(common.venue_locality(
                    "Auditório do Ramo Grande e Centro Cultural e de Congressos de Angra do Heroísmo"))


if __name__ == "__main__":
    unittest.main()
