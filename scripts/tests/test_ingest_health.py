"""Regression tests for visible source failures and safe ingestion writes."""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

import ingest_cmpv
import ingest_museu_angra
import ingest_whatson_azores
from ingest_health import SourceError, _duplicate, run_ingester
import yaml


class SourceFailureTests(unittest.TestCase):
    def test_http_failure_is_not_a_successful_empty_scan(self):
        for module in (ingest_museu_angra, ingest_cmpv, ingest_whatson_azores):
            with self.subTest(source=module.__name__), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "events.yml"
                path.write_text("[]\n", encoding="utf-8")
                error = HTTPError("https://example.test/agenda", 403, "Forbidden", {}, None)
                with patch("urllib.request.urlopen", side_effect=error), patch.object(
                    sys, "argv", [module.__name__, "--dry-run", "--yaml-path", str(path)]
                ), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(module.main(), 1)
                self.assertEqual(path.read_text(encoding="utf-8"), "[]\n")

    def test_partial_discovery_failure_preserves_yaml_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, report = Path(tmp) / "events.yml", Path(tmp) / "health.json"
            path.write_text("[]\n", encoding="utf-8")

            def discover(today, lookahead, health):
                health.pages = 1
                health.listed = 3
                health.parsed = 2
                raise SourceError("required page 2 returned 403")

            with patch.object(sys, "argv", ["test", "--yaml-path", str(path), "--health-report", str(report)]):
                self.assertEqual(run_ingester("fixture", discover), 1)
            self.assertEqual(path.read_text(), "[]\n")
            health = json.loads(report.read_text())
            self.assertEqual(health["status"], "degraded")
            self.assertEqual(health["parsed"], 2)

    def test_unexpected_parser_failure_also_has_a_health_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, report = Path(tmp) / "events.yml", Path(tmp) / "health.json"
            path.write_text("[]\n", encoding="utf-8")
            with patch.object(sys, "argv", ["test", "--yaml-path", str(path), "--health-report", str(report)]), \
                 patch("ingest_health.load_existing_yaml", side_effect=TypeError("schema mismatch")):
                self.assertEqual(run_ingester("fixture", lambda *args: []), 1)
            self.assertEqual(json.loads(report.read_text())["status"], "degraded")

    def test_ongoing_ranges_deduplication_and_cap_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, report = Path(tmp) / "events.yml", Path(tmp) / "health.json"
            path.write_text("[]\n", encoding="utf-8")
            ongoing = {"date": dt.date(2026, 9, 1), "end_date": dt.date(2026, 11, 1),
                       "name": "Exposição de teste", "venue": "Museu de Angra", "source_url": "https://example.test/a"}
            future = dict(ongoing, date=dt.date(2026, 10, 20), name="Oficina de pintura", source_url="https://example.test/b")
            with patch.object(sys, "argv", ["test", "--yaml-path", str(path), "--health-report", str(report),
                                           "--today", "2026-10-10", "--max-events", "1"]):
                self.assertEqual(run_ingester("fixture", lambda *args: [ongoing, ongoing, future]), 0)
            data = yaml.safe_load(path.read_text())
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["end_date"], dt.date(2026, 11, 1))
            health = json.loads(report.read_text())
            self.assertEqual((health["candidates"], health["duplicates"], health["deferred"], health["added"]), (2, 1, 1, 1))

    def test_same_movie_at_two_venues_is_not_collapsed(self):
        first = {"date": dt.date(2026, 10, 11), "name": "Cinema: Verity", "venue": "Auditório do Ramo Grande"}
        candidate = dict(first, name="Verity", venue="Centro Cultural e de Congressos de Angra do Heroísmo")
        self.assertFalse(_duplicate(candidate, [first]))
        candidate["venue"] = "Auditório Ramo Grande"
        self.assertTrue(_duplicate(candidate, [first]))

    def test_series_dates_and_short_artist_titles_match_existing(self):
        date = dt.date(2027, 1, 16)
        existing = [{"date": date, "name": "Concertos Únicos 2027: Ana Moura com João Barros",
                     "venue": "Auditório do Ramo Grande"}]
        candidate = {"date": date, "name": "Concertos Únicos – 5.ª Edição 2027", "venue": "Auditório Ramo Grande"}
        self.assertTrue(_duplicate(candidate, existing))
        candidate["date"] = dt.date(2027, 3, 13)
        self.assertFalse(_duplicate(candidate, existing))


if __name__ == "__main__":
    unittest.main()
