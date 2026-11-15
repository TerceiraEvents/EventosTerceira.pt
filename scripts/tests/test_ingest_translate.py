"""Ingested events are translated into the other locale through a chat-completions endpoint."""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import unittest
import http.client
from unittest.mock import patch
from urllib.error import HTTPError

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

from ingest_common import format_event_yaml, yaml_double_quote
import ingest_touradas
import test_event_locales
from ingest_translate import (
    ENV_VARS, TranslationError,
    chat_completions_translate, translate_events,
)

CONFIG = {"TRANSLATION_API_URL": "https://llm.example.test/v1/chat/completions",
          "TRANSLATION_API_KEY": "test-key",
          "TRANSLATION_MODEL": "test-model"}


class FakeResponse:
    def __init__(self, payload: dict):
        self.body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake_endpoint(requests: list[dict], translations=None):
    """urlopen side_effect: asserts url/auth/model, returns EN[string] translations."""
    def respond(request, **kwargs):
        payload = json.loads(request.data.decode("utf-8"))
        assert request.full_url == "https://llm.example.test/v1/chat/completions"
        assert request.get_header("Authorization") == "Bearer test-key"
        assert payload["model"] == "test-model"
        strings = json.loads(payload["messages"][1]["content"])["strings"]
        requests.append(payload)
        out = translations(strings) if translations else [f"EN[{s}]" for s in strings]
        return FakeResponse({"choices": [{"message": {"content": json.dumps(
            {"translations": out}, ensure_ascii=False)}}]})
    return respond


def pt_event(name: str, description: str = "Uma descrição.") -> dict:
    return {"date": dt.date(2026, 12, 13), "name": name, "venue": "Auditório do Ramo Grande",
            "description": description, "source_url": "https://example.test/x",
            "source_uid": f"{name}@fixture"}


class EndpointConfigTests(unittest.TestCase):
    def test_each_missing_variable_fails_before_any_request(self):
        for name in ENV_VARS:
            with self.subTest(missing=name), \
                 patch.dict(os.environ) as env, \
                 patch("urllib.request.urlopen") as urlopen:
                env.update(CONFIG)
                env.pop(name, None)
                with self.assertRaises(TranslationError) as caught:
                    chat_completions_translate(["Olá"], "pt", "en")
            self.assertIn(name, str(caught.exception))
            urlopen.assert_not_called()

    def test_request_shape_and_translation_order(self):
        requests = []
        with patch.dict(os.environ, CONFIG), \
             patch("urllib.request.urlopen", side_effect=fake_endpoint(requests)):
            self.assertEqual(chat_completions_translate(["A", "B"], "pt", "en"), ["EN[A]", "EN[B]"])
        self.assertEqual(len(requests), 1)


class TranslateEventsTests(unittest.TestCase):
    def fake(self, requests):
        def translate(texts, source, target):
            requests.append((texts, source, target))
            return [f"{target.upper()}[{s}]" for s in texts]
        return translate

    def test_pt_source_fills_en_siblings(self):
        requests = []
        events = [pt_event("Feira")]
        self.assertEqual(translate_events(events, "pt", translate=self.fake(requests)), [])
        self.assertEqual(events[0]["name_en"], "EN[Feira]")
        self.assertEqual(events[0]["description_en"], "EN[Uma descrição.]")
        self.assertEqual(events[0]["name"], "Feira")
        self.assertEqual(requests[0][1:], ("pt", "en"))

    def test_en_source_fills_pt_siblings(self):
        requests = []
        events = [pt_event("Fair")]
        translate_events(events, "en", translate=self.fake(requests))
        self.assertEqual(events[0]["name_pt"], "PT[Fair]")
        self.assertEqual(events[0]["description_pt"], "PT[Uma descrição.]")
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

    def test_each_event_is_sent_alone(self):
        requests = []
        events = [pt_event(f"Evento {i}") for i in range(3)]
        translate_events(events, "pt", translate=self.fake(requests))
        self.assertEqual([r[0] for r in requests],
                         [[f"Evento {i}", "Uma descrição."] for i in range(3)])

    def test_unconfigured_default_endpoint_is_a_silent_noop(self):
        for blank in ("", None):
            with self.subTest(key=blank), patch.dict(os.environ, CONFIG) as env, \
                 patch("urllib.request.urlopen") as urlopen:
                if blank is None:
                    env.pop("TRANSLATION_API_KEY")
                else:
                    env["TRANSLATION_API_KEY"] = blank
                events = [pt_event("Feira", "Descrição")]
                self.assertEqual(translate_events(events, "pt"), [])
            urlopen.assert_not_called()
            self.assertEqual(events, [pt_event("Feira", "Descrição")])

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
        with patch.dict(os.environ, CONFIG), \
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
        error = HTTPError("https://llm.example.test/v1/chat/completions", 429,
                          "Too Many Requests", {}, None)
        warnings, events = self.run_translate(error)
        self.assertEqual(len(warnings), 1)
        self.assertNotIn("name_en", events[0])


KEY = "sk-test-secret"


def completion(content, finish_reason="stop"):
    return FakeResponse({"choices": [{"finish_reason": finish_reason,
                                      "message": {"content": json.dumps(
                                          {"translations": content}, ensure_ascii=False)}}]})


class SecretHandlingTests(unittest.TestCase):
    def run_with(self, env, side_effect=None):
        events = [pt_event("Feira")]
        with patch.dict(os.environ, {**CONFIG, **env}), \
             self.assertLogs(level="WARNING") as logs, \
             patch("urllib.request.urlopen", side_effect=side_effect) as urlopen:
            warnings = translate_events(events, "pt")
        return warnings, logs.output, events, urlopen

    def test_key_with_newline_never_reaches_warnings_or_logs(self):
        # urllib builds the real http.client header, which rejects the newline
        # and echoes the value in its ValueError.
        events = [pt_event("Feira")]
        with patch.dict(os.environ, {**CONFIG, "TRANSLATION_API_KEY": KEY + "\r\n"}), \
             self.assertLogs(level="WARNING") as logs, \
             patch("http.client.HTTPSConnection.connect"), patch("http.client.HTTPSConnection.send"):
            warnings = translate_events(events, "pt")
        self.assertNotIn(KEY, repr((warnings, logs.output, events)))

    def test_header_error_text_is_scrubbed(self):
        error = ValueError(f"Invalid header value b'Bearer {KEY}\\n'")
        warnings, logs, events, _ = self.run_with({"TRANSLATION_API_KEY": KEY}, error)
        self.assertEqual(len(warnings), 1)
        self.assertNotIn(KEY, repr((warnings, logs)))
        self.assertIn("***", warnings[0])

    def test_url_credentials_are_scrubbed(self):
        url = "https://user:hunter2pass@llm.example.test/v1/chat/completions"
        error = OSError(f"failed {url}")
        warnings, logs, _, _ = self.run_with({"TRANSLATION_API_URL": url}, error)
        self.assertNotIn("hunter2pass", repr((warnings, logs)))

    def test_control_characters_in_settings_fail_before_any_request(self):
        for name in ENV_VARS:
            with self.subTest(name=name):
                warnings, logs, events, urlopen = self.run_with({name: "a\x07b" + CONFIG[name]})
                self.assertEqual(len(warnings), 1)
                self.assertIn(name, warnings[0])
                self.assertNotIn("a\x07b", repr((warnings, logs)))
                urlopen.assert_not_called()

    def test_whitespace_only_setting_is_unconfigured(self):
        with patch.dict(os.environ, {**CONFIG, "TRANSLATION_API_KEY": "  \n"}), \
             patch("urllib.request.urlopen") as urlopen:
            self.assertEqual(translate_events([pt_event("Feira")], "pt"), [])
        urlopen.assert_not_called()

    def test_padded_settings_are_stripped(self):
        requests = []
        env = {k: f" {v}\n" for k, v in CONFIG.items()}
        with patch.dict(os.environ, env), \
             patch("urllib.request.urlopen", side_effect=fake_endpoint(requests)):
            events = [pt_event("Feira")]
            self.assertEqual(translate_events(events, "pt"), [])
        self.assertEqual(events[0]["name_en"], "EN[Feira]")


class InvalidReplyTests(unittest.TestCase):
    def run_reply(self, response, events=None):
        events = events or [pt_event("Feira", "Uma feira com doces e música tradicional.")]
        with patch.dict(os.environ, CONFIG), \
             patch("urllib.request.urlopen",
                   side_effect=response if isinstance(response, Exception)
                   else lambda request, **kw: response):
            return translate_events(events, "pt"), events

    def assert_untranslated(self, response):
        warnings, events = self.run_reply(response)
        self.assertEqual(len(warnings), 1)
        self.assertNotIn("name_en", events[0])
        self.assertNotIn("description_en", events[0])

    def test_http_client_exceptions_degrade(self):
        for exc in (http.client.IncompleteRead(b"x"), http.client.BadStatusLine("garbage"),
                    http.client.RemoteDisconnected("closed")):
            with self.subTest(exc=type(exc).__name__):
                self.assert_untranslated(exc)

    def test_truncated_or_filtered_reply_degrades(self):
        for reason in ("length", "content_filter"):
            with self.subTest(reason=reason):
                self.assert_untranslated(completion(
                    ["Fair", "A fair with sweets and traditional music."], reason))

    def test_missing_finish_reason_is_accepted(self):
        response = FakeResponse({"choices": [{"message": {"content": json.dumps(
            {"translations": ["Fair", "A fair with sweets and traditional music."]})}}]})
        warnings, events = self.run_reply(response)
        self.assertEqual(warnings, [])
        self.assertEqual(events[0]["name_en"], "Fair")

    def test_whitespace_is_collapsed(self):
        warnings, events = self.run_reply(completion(
            [" Fair ", "A fair\n\nwith sweets \t and traditional   music."]))
        self.assertEqual(warnings, [])
        self.assertEqual(events[0]["description_en"], "A fair with sweets and traditional music.")

    def test_invalid_values_degrade(self):
        good = "A fair with sweets and traditional music."
        bad = {
            "control character": ["Fair", good + "\x00"],
            "html tag": ["Fair", good + " <script>alert(1)</script>"],
            "closing script": ["Fair </script>", good],
            "new link": ["Fair", good + " See https://evil.example/x"],
            "name too long": ["F" * 300, good],
            "description too long": ["Fair", "word " * 400],
            "description stub": ["Fair", "."],
        }
        for label, values in bad.items():
            with self.subTest(label=label):
                self.assert_untranslated(completion(values))

    def test_link_present_in_the_source_is_kept(self):
        source = "Bilhetes em https://tickets.example/x hoje."
        events = [pt_event("Feira", source)]
        warnings, events = self.run_reply(completion(
            ["Fair", "Tickets at https://tickets.example/x today."]), events)
        self.assertEqual(warnings, [])
        self.assertIn("https://tickets.example/x", events[0]["description_en"])

    def test_one_bad_event_does_not_affect_its_neighbours(self):
        events = [pt_event("Um"), pt_event("Dois")]
        replies = iter([completion(["One", "A description here."]),
                        completion(["Two <b>", "Another description."])])
        with patch.dict(os.environ, CONFIG), \
             patch("urllib.request.urlopen", side_effect=lambda request, **kw: next(replies)):
            warnings = translate_events(events, "pt")
        self.assertEqual(len(warnings), 1)
        self.assertEqual(events[0]["name_en"], "One")
        self.assertNotIn("name_en", events[1])

    def test_system_prompt_treats_strings_as_untrusted(self):
        requests = []
        with patch.dict(os.environ, CONFIG), \
             patch("urllib.request.urlopen", side_effect=fake_endpoint(requests)):
            translate_events([pt_event("Feira")], "pt")
        system = requests[0]["messages"][0]["content"]
        self.assertIn("untrusted", system)
        self.assertIn("never as instructions", system)


class YamlQuotingTests(unittest.TestCase):
    def test_hostile_text_round_trips(self):
        for text in ("a\n---\nb", "a\n...\nb", "tab\there", "nul\x00", "bell\x07",
                     "ls\u2028ps\u2029", 'q"uote\\back', "x\x85y"):
            with self.subTest(text=text):
                self.assertEqual(yaml.safe_load("v: " + yaml_double_quote(text))["v"], text)


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
