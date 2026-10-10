"""Run event discovery with explicit health reports and validated writes."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import datetime as dt
import json
import logging
import os
import re
from pathlib import Path
import sys
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

import yaml

from ingest_common import (
    DEFAULT_MAX_EVENTS, LOOKAHEAD_DAYS, USER_AGENT, YAML_PATH,
    format_event_yaml, is_similar_match, load_existing_yaml, normalize_name,
)


class SourceError(RuntimeError):
    """A source cannot provide a complete, recognized event listing."""


@dataclass
class SourceHealth:
    """Discovery and reconciliation counters for one source invocation."""

    source: str
    status: str = "running"
    pages: int = 0
    listed: int = 0
    local: int = 0
    parsed: int = 0
    rejected: int = 0
    duplicates: int = 0
    outside_window: int = 0
    candidates: int = 0
    deferred: int = 0
    added: int = 0
    corrections: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    known_events: list[dict] = field(default_factory=list, repr=False)

    def fetch(self, url: str, payload: dict | None = None) -> bytes:
        """Fetch a public page or read-only JSON query, raising on failure."""
        headers = {"User-Agent": USER_AGENT}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, headers=headers, data=data)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise SourceError(f"{url}: {exc}") from exc
        self.pages += 1
        if not content.strip():
            raise SourceError(f"{url}: empty response")
        return content


def _venue_key(venue: str, name: str = "") -> str:
    text = normalize_name(venue).split("|")[0].strip()
    if "cccah" in text or "centro cultural e de congressos" in text:
        return "cccah"
    if "ramo grande" in text:
        return "ramo grande"
    if "pacos" in text and "concelho" in text:
        return "pacos praia" if "praia" in text else "pacos angra"
    if "museu de angra" in text or "igreja de nossa senhora da guia" in text:
        return "museu angra"
    if "sao bento" in text or (text == "angra do heroismo" and "sao bento" in normalize_name(name)):
        return "sao bento"
    return " ".join(word for word in re.findall(r"\w+", text) if word not in {"de", "do", "da", "e"})


def _duplicate(event: dict, existing: list[dict]) -> bool:
    for other in existing:
        start = other.get("date")
        end = other.get("end_date", start)
        if not isinstance(start, dt.date) or not isinstance(end, dt.date):
            continue
        if not start <= event["date"] <= end:
            continue
        if event.get("source_uid") and event["source_uid"] == other.get("source_uid"):
            return True
        if event.get("source_url") and event["source_url"] == other.get("source_url"):
            return True
        venue = _venue_key(event["venue"], event["name"])
        other_venue = _venue_key(other.get("venue", ""), other.get("name", ""))
        if not venue or not other_venue or not (venue.startswith(other_venue) or other_venue.startswith(venue)):
            continue
        film_names = [re.sub(r"^cinema\s*:\s*", "", normalize_name(name))
                      for name in (event["name"], other.get("name", ""))]
        film_names = [re.sub(r"\s*\((?:praia da vitoria|angra do heroismo)\)$", "", name) for name in film_names]
        if film_names[0] == film_names[1]:
            return True
        if any(is_similar_match(event["name"], other.get(key, "")) for key in ("name", "name_en")):
            return True
        names = [normalize_name(event["name"]), normalize_name(other.get("name", ""))]
        for first, second in (names, names[::-1]):
            phrase = first.split(":")[0].strip()
            if len(re.findall(r"\w+", phrase)) >= 2 and phrase in second:
                return True
        prefixes = [set(re.findall(r"[^\W\d_]+", name.split(":")[0])) - {"a", "de", "edicao"}
                    for name in names]
        if len(prefixes[0]) >= 2 and prefixes[0] == prefixes[1]:
            return True
        words = set(re.findall(r"\w+", normalize_name(other.get("name", "")))) - {
            "a", "o", "as", "os", "de", "do", "da", "dos", "das", "e", "com",
            "apresentacao", "album", "concerto", "concertos", "estreia", "edicao",
        }
        description_words = set(re.findall(r"\w+", normalize_name(event.get("description", ""))))
        if len(words) >= 3 and words <= description_words:
            return True
    return False


def run_ingester(source: str, discover) -> int:
    """Discover, reconcile, and append events; fail before writing on bad coverage."""
    parser = argparse.ArgumentParser(description=f"Ingest verified events from {source}.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-events", type=int, default=DEFAULT_MAX_EVENTS)
    parser.add_argument("--yaml-path", type=Path, default=YAML_PATH)
    parser.add_argument("--health-report", type=Path)
    parser.add_argument("--today", type=dt.date.fromisoformat,
                        default=dt.datetime.now(ZoneInfo("Atlantic/Azores")).date())
    parser.add_argument("--lookahead-days", type=int, default=LOOKAHEAD_DAYS)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    if args.max_events < 1 or args.lookahead_days < 0:
        parser.error("max-events must be positive and lookahead-days non-negative")
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(message)s")
    health = SourceHealth(source)
    try:
        lookahead = args.today + dt.timedelta(days=args.lookahead_days)
        existing = load_existing_yaml(args.yaml_path)
        health.known_events = existing
        events = discover(args.today, lookahead, health)
        candidates = []
        for event in events:
            start = event.get("date")
            end = event.get("end_date", start)
            if not isinstance(start, dt.date) or not isinstance(end, dt.date) or end < start:
                raise SourceError(f"Invalid date range: {event.get('name')}")
            if not event.get("name") or not event.get("venue") or not event.get("source_url"):
                raise SourceError(f"Missing title, venue, or source: {event}")
            if end < args.today or start > lookahead:
                health.outside_window += 1
            else:
                match = next((other for other in existing + candidates if _duplicate(event, [other])), None)
                if match is None:
                    candidates.append(event)
                else:
                    health.duplicates += 1
                    if event.get("time") and match.get("time") and event["time"] != match["time"]:
                        health.corrections.append({"date": start.isoformat(), "name": event["name"],
                                                   "field": "time", "stored": match["time"],
                                                   "observed": event["time"], "source_url": event["source_url"]})
        candidates.sort(key=lambda event: (event["date"], event.get("time") or "", event["name"]))
        health.candidates = len(candidates)
        health.deferred = max(0, len(candidates) - args.max_events)
        selected = candidates[:args.max_events]
        if selected:
            block = f"\n# Auto-ingested from {source} ({args.today.isoformat()})\n"
            block += "\n".join(format_event_yaml(event) for event in selected)
            if args.dry_run:
                sys.stdout.write(block)
            else:
                original = args.yaml_path.read_text(encoding="utf-8")
                if not existing:
                    original = re.sub(r"(?m)^\s*\[\]\s*(?=#|$)", "", original)
                output = original + block
                parsed_output = yaml.safe_load(output)
                if not isinstance(parsed_output, list) or len(parsed_output) != len(existing) + len(selected):
                    raise SourceError("Generated YAML does not preserve the existing event list")
                args.yaml_path.write_text(output, encoding="utf-8")
                health.added = len(selected)
        health.status = "healthy"
    except Exception as exc:
        health.status = "degraded"
        health.errors.append(f"{type(exc).__name__}: {exc}")
        logging.error("%s discovery incomplete: %s", source, exc)
    report = json.dumps({key: value for key, value in asdict(health).items() if key != "known_events"},
                        ensure_ascii=False, sort_keys=True)
    logging.info("SOURCE_HEALTH %s", report)
    if args.health_report:
        args.health_report.write_text(report + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
            stream.write(f"### {source}: {health.status}\n\n```json\n{report}\n```\n")
    return 0 if health.status == "healthy" else 1
