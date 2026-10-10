"""Date semantics for published Portuguese event programmes."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
from ingest_dates import published_dates, published_time


class CalendarDatesTests(unittest.TestCase):
    def test_published_sessions_and_ranges(self):
        cases = [
            ("10 de outubro | 15:00", [("2026-10-10", "2026-10-10")]),
            ("De 3 a 10 de outubro", [("2026-10-03", "2026-10-10")]),
            ("27 e 28 de Novembro", [("2026-11-27", "2026-11-27"), ("2026-11-28", "2026-11-28")]),
            ("3 e 10 de outubro | 21:00 - 23:00", [("2026-10-03", "2026-10-03"), ("2026-10-10", "2026-10-10")]),
            ("3 e 10 de outubro de 2026 - 21h30", [("2026-10-03", "2026-10-03"), ("2026-10-10", "2026-10-10")]),
            ("Sábado 3 e sábado 10 de outubro", [("2026-10-03", "2026-10-03"), ("2026-10-10", "2026-10-10")]),
            ("Dia 3 e dia 10 de outubro", [("2026-10-03", "2026-10-03"), ("2026-10-10", "2026-10-10")]),
            ("dias 3 e 10 de outubro", [("2026-10-03", "2026-10-03"), ("2026-10-10", "2026-10-10")]),
            ("Entre 3 e 10 de outubro", [("2026-10-03", "2026-10-10")]),
            ("entre 3 de outubro e 10 de novembro", [("2026-10-03", "2026-11-10")]),
            ("20 de Setembro a 13 de Dezembro", [("2026-09-20", "2026-12-13")]),
            ("16 de janeiro, 13 de março e 17 de abril de 2027", [
                ("2027-01-16", "2027-01-16"), ("2027-03-13", "2027-03-13"), ("2027-04-17", "2027-04-17")]),
            ("04.10.2026 - 25.10.2026", [("2026-10-04", "2026-10-25")]),
            ("31 de dezembro de 2026 a 2 de janeiro de 2027", [("2026-12-31", "2027-01-02")]),
        ]
        for label, expected in cases:
            with self.subTest(label=label):
                parsed = published_dates(label, 2026)
                self.assertEqual(parsed, [(dt.date.fromisoformat(a), dt.date.fromisoformat(b)) for a, b in expected])

    def test_unknown_or_impossible_dates_fail(self):
        for label in ("Até 23 de novembro", "A partir de 16 de setembro", "coming soon", "31 de fevereiro",
                      "28 de novembro a 3 de dezembro, 10 de dezembro", "1 a 3 e 10 de outubro",
                      "3 de outubro e 10 a 12 de novembro"):
            with self.subTest(label=label), self.assertRaises(ValueError):
                published_dates(label, 2026)

    def test_time_is_explicit_and_valid(self):
        for label, expected in (("21h30", "21:30"), ("21h", "21:00"), ("14H00 – 18H00", "14:00"), ("00:00", "00:00"),
                                ("Horário a definir", None), ("29h15", None), ("Duração: 2 horas", None),
                                ("Sala 3 h", None), ("Duração aproximada: 1h30", None),
                                ("AJAIT: de segunda a sexta das 08h30-13h00", None)):
            with self.subTest(label=label):
                self.assertEqual(published_time(label), expected)


if __name__ == "__main__":
    unittest.main()
