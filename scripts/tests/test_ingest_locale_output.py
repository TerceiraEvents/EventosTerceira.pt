"""Ingested Portuguese-only events are written with both locales."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

from ingest_health import run_ingester
import test_event_locales


class FakeResponse:
    def __init__(self, payload: dict):
        self.body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake_models_endpoint(requests: list):
    """urlopen side_effect: asserts the Bearer token, returns EN<string> translations."""
    def respond(request, **kwargs):
        assert request.get_header("Authorization") == "Bearer test-token"
        payload = json.loads(request.data.decode("utf-8"))
        strings = json.loads(payload["messages"][1]["content"])["strings"]
        requests.append(payload)
        return FakeResponse({"choices": [{"message": {"content": json.dumps(
            {"translations": [f"EN<{s}>" for s in strings]}, ensure_ascii=False)}}]})
    return respond


class RunIngesterIntegrationTests(unittest.TestCase):
    def test_ingested_events_get_the_other_locale(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.yml"
            path.write_text("[]\n", encoding="utf-8")
            events = [
                {"date": dt.date(2026, 12, 13), "name": "BATUKES – UM DIA DE NATAL",
                 "venue": "Auditório do Ramo Grande",
                 "description": "Um dia de Natal onde a imaginação ganha ritmo…",
                 "source_url": "https://example.test/batukes",
                 "source_uid": "batukes@fixture"},
                {"date": dt.date(2026, 12, 20), "name": "Mercado de Natal",
                 "venue": "Praça Velha",
                 "description": "📅 20 de dezembro · artesanato e doces regionais.",
                 "source_url": "https://example.test/mercado",
                 "source_uid": "mercado@fixture"},
            ]
            requests = []
            with patch.dict(os.environ, {"GITHUB_MODELS_TOKEN": "test-token"}), \
                 patch("urllib.request.urlopen", side_effect=fake_models_endpoint(requests)), \
                 patch.object(sys, "argv", ["fixture", "--yaml-path", str(path), "--today", "2026-11-15"]):
                self.assertEqual(run_ingester("fixture", lambda *args: [dict(e) for e in events]), 0)
            written = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(len(written), 2)
            self.assertEqual(test_event_locales.audit(written), [])
            batukes = next(e for e in written if e["name"] == "BATUKES – UM DIA DE NATAL")
            self.assertEqual(batukes["name_en"], "EN<BATUKES – UM DIA DE NATAL>")
            self.assertEqual(batukes["description_en"], "EN<Um dia de Natal onde a imaginação ganha ritmo…>")

    def test_translation_failure_still_writes_source_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, report = Path(tmp) / "events.yml", Path(tmp) / "health.json"
            path.write_text("[]\n", encoding="utf-8")
            events = [{"date": dt.date(2026, 12, 13), "name": "Feira",
                       "venue": "Auditório do Ramo Grande",
                       "description": "Uma descrição.",
                       "source_url": "https://example.test/x",
                       "source_uid": "Feira@fixture"}]
            with patch.dict(os.environ) as env, \
                 patch("urllib.request.urlopen") as urlopen, \
                 patch.object(sys, "argv", ["fixture", "--yaml-path", str(path),
                                            "--health-report", str(report), "--today", "2026-11-15"]):
                env.pop("GITHUB_MODELS_TOKEN", None)
                self.assertEqual(run_ingester("fixture", lambda *args: events), 0)
            urlopen.assert_not_called()
            written = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(len(written), 1)
            self.assertNotIn("name_en", written[0])
            health = json.loads(report.read_text())
            self.assertEqual(health["status"], "healthy")
            self.assertTrue(any("Translation" in w for w in health["warnings"]))


if __name__ == "__main__":
    unittest.main()
