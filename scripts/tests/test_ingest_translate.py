"""Ingested events are translated into the other locale via GitHub Models."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

from ingest_common import format_event_yaml
from ingest_health import run_ingester
import ingest_touradas
import test_event_locales

try:
    from ingest_translate import (
        BATCH_SIZE, MODEL, TOKEN_ENV, TranslationError,
        github_models_translate, translate_events,
    )
except ImportError:  # pre-fix tree has no translation module
    BATCH_SIZE, MODEL, TOKEN_ENV = 10, "", ""
    TranslationError = Exception
    github_models_translate = translate_events = None


class FakeResponse:
    def __init__(self, payload: dict):
        self.body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake_models_endpoint(requests: list[dict], translations=None):
    """urlopen side_effect: asserts auth/model, returns EN<string> translations."""
    def respond(request, **kwargs):
        payload = json.loads(request.data.decode("utf-8"))
        assert request.get_header("Authorization") == "Bearer test-token"
        assert payload["model"] == MODEL
        strings = json.loads(payload["messages"][1]["content"])["strings"]
        requests.append(payload)
        out = translations(strings) if translations else [f"EN<{s}>" for s in strings]
        return FakeResponse({"choices": [{"message": {"content": json.dumps(
            {"translations": out}, ensure_ascii=False)}}]})
    return respond


def pt_event(name: str, description: str = "Uma descrição.") -> dict:
    return {"date": dt.date(2026, 12, 13), "name": name, "venue": "Auditório do Ramo Grande",
            "description": description, "source_url": "https://example.test/x",
            "source_uid": f"{name}@fixture"}


class ModelsEndpointTests(unittest.TestCase):
    def test_missing_token_fails_before_any_request(self):
        with patch.dict(os.environ) as env, \
             patch("urllib.request.urlopen") as urlopen:
            env.pop(TOKEN_ENV, None)
            with self.assertRaises(TranslationError) as caught:
                github_models_translate(["Olá"], "pt", "en")
        self.assertIn(TOKEN_ENV, str(caught.exception))
        urlopen.assert_not_called()

    def test_request_shape_and_translation_order(self):
        requests = []
        with patch.dict(os.environ, {TOKEN_ENV: "test-token"}), \
             patch("urllib.request.urlopen", side_effect=fake_models_endpoint(requests)):
            self.assertEqual(github_models_translate(["A", "B"], "pt", "en"), ["EN<A>", "EN<B>"])
        self.assertEqual(len(requests), 1)


class TranslateEventsTests(unittest.TestCase):
    def fake(self, requests):
        def translate(texts, source, target):
            requests.append((texts, source, target))
            return [f"{target.upper()}<{s}>" for s in texts]
        return translate

    def test_pt_source_fills_en_siblings(self):
        requests = []
        events = [pt_event("Feira")]
        self.assertEqual(translate_events(events, "pt", translate=self.fake(requests)), [])
        self.assertEqual(events[0]["name_en"], "EN<Feira>")
        self.assertEqual(events[0]["description_en"], "EN<Uma descrição.>")
        self.assertEqual(events[0]["name"], "Feira")
        self.assertEqual(requests[0][1:], ("pt", "en"))

    def test_en_source_fills_pt_siblings(self):
        requests = []
        events = [pt_event("Fair")]
        translate_events(events, "en", translate=self.fake(requests))
        self.assertEqual(events[0]["name_pt"], "PT<Fair>")
        self.assertEqual(events[0]["description_pt"], "PT<Uma descrição.>")
        self.assertEqual(requests[0][1:], ("en", "pt"))

    def test_existing_sibling_is_not_retranslated(self):
        requests = []
        events = [pt_event("Feira")]
        events[0]["name_en"] = "Fair"
        translate_events(events, "pt", translate=self.fake(requests))
        self.assertEqual(requests[0][0], ["Uma descrição."])
        self.assertEqual(events[0]["name_en"], "Fair")

    def test_missing_description_sends_only_the_name(self):
        requests = []
        events = [pt_event("Feira")]
        del events[0]["description"]
        translate_events(events, "pt", translate=self.fake(requests))
        self.assertEqual(requests[0][0], ["Feira"])

    def test_batches_chunk_to_batch_size(self):
        requests = []
        events = [pt_event(f"Evento {i}") for i in range(BATCH_SIZE + 2)]
        translate_events(events, "pt", translate=self.fake(requests))
        self.assertEqual(len(requests), 2)
        self.assertEqual([len(r[0]) for r in requests], [BATCH_SIZE * 2, 4])

    def test_failure_warns_and_keeps_source_text(self):
        def failing(texts, source, target):
            raise TranslationError("boom")
        events = [pt_event("Feira")]
        warnings = translate_events(events, "pt", translate=failing)
        self.assertEqual(len(warnings), 1)
        self.assertIn("Feira", warnings[0])
        self.assertNotIn("name_en", events[0])


class HttpFailureTests(unittest.TestCase):
    def run_translate(self, response_or_error, events=None):
        events = events or [pt_event("Feira")]
        with patch.dict(os.environ, {TOKEN_ENV: "test-token"}), \
             patch("urllib.request.urlopen",
                   side_effect=response_or_error if isinstance(response_or_error, Exception)
                   else lambda request, **kw: response_or_error):
            warnings = translate_events(events, "pt")
        return warnings, events

    def test_wrong_translation_count(self):
        warnings, events = self.run_translate(FakeResponse(
            {"choices": [{"message": {"content": '{"translations": ["só uma"]}'}}]}))
        self.assertEqual(len(warnings), 1)
        self.assertNotIn("name_en", events[0])

    def test_empty_translation(self):
        warnings, events = self.run_translate(FakeResponse(
            {"choices": [{"message": {"content": '{"translations": ["  ", "ok"]}'}}]}))
        self.assertEqual(len(warnings), 1)
        self.assertNotIn("name_en", events[0])

    def test_non_json_content(self):
        warnings, events = self.run_translate(FakeResponse(
            {"choices": [{"message": {"content": "not json"}}]}))
        self.assertEqual(len(warnings), 1)
        self.assertNotIn("name_en", events[0])

    def test_http_error(self):
        error = HTTPError("https://models.github.ai/inference/chat/completions", 429,
                          "Too Many Requests", {}, None)
        warnings, events = self.run_translate(error)
        self.assertEqual(len(warnings), 1)
        self.assertNotIn("name_en", events[0])


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
            events = [pt_event("Feira")]
            with patch.dict(os.environ) as env, \
                 patch("urllib.request.urlopen") as urlopen, \
                 patch.object(sys, "argv", ["fixture", "--yaml-path", str(path),
                                            "--health-report", str(report), "--today", "2026-11-15"]):
                env.pop(TOKEN_ENV, None)
                self.assertEqual(run_ingester("fixture", lambda *args: events), 0)
            urlopen.assert_not_called()
            written = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(len(written), 1)
            self.assertNotIn("name_en", written[0])
            health = json.loads(report.read_text())
            self.assertEqual(health["status"], "healthy")
            self.assertTrue(any("Translation" in w for w in health["warnings"]))


class FormatEventYamlTests(unittest.TestCase):
    def test_locale_siblings_follow_their_bare_field(self):
        event = pt_event("Feira")
        event.update({"name_en": "Fair", "name_pt": "Feira",
                      "description_en": "A fair.", "description_pt": "Uma feira."})
        block = format_event_yaml(event)
        lines = block.splitlines()
        name_i = lines.index('  name: "Feira"')
        self.assertEqual(lines[name_i + 1:name_i + 3],
                         ['  name_en: "Fair"', '  name_pt: "Feira"'])
        desc_i = lines.index('  description: "Uma descrição."')
        self.assertEqual(lines[desc_i + 1:desc_i + 3],
                         ['  description_en: "A fair."', '  description_pt: "Uma feira."'])
        parsed = yaml.safe_load(block)[0]
        self.assertEqual(parsed["name_en"], "Fair")
        self.assertEqual(parsed["description_pt"], "Uma feira.")


class TouradasTemplatesTests(unittest.TestCase):
    def test_handwritten_english_siblings(self):
        source = ingest_touradas.JUNTA_SOURCES[0]
        html = ("Calendário de festas: Tourada à corda no dia 15 de junho de 2026 "
                "com ganadeiro: Marcos Bastos.")
        with patch.object(ingest_touradas, "_fetch", return_value=html):
            events = ingest_touradas.harvest_junta(source, dt.date(2026, 1, 1))
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["name_en"],
                         f"Tourada à Corda (Rope Bullfight) — {source.venue}")
        self.assertIn("traditional street bullfight", event["description_en"])
        self.assertIn("Ganadeiro: Marcos Bastos.", event["description_en"])
        self.assertEqual(test_event_locales.missing_locales(event, "name"), [])
        self.assertEqual(test_event_locales.missing_locales(event, "description"), [])


if __name__ == "__main__":
    unittest.main()
