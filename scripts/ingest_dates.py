"""Parse explicitly published Portuguese calendar dates and session times."""
from __future__ import annotations

import datetime as dt
import re

from ingest_common import clean_description, normalize_name

MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
MONTH_RE = "|".join(MONTHS)


def published_dates(text: str, year: int) -> list[tuple[dt.date, dt.date]]:
    """Return discrete sessions or an inclusive range from an explicit date label."""
    text = normalize_name(clean_description(text))
    between = bool(re.match(r"^entre\b", text))
    explicit_years = re.findall(r"\b(20\d{2})\b", text)
    if explicit_years:
        year = int(explicit_years[-1])
    if re.match(r"(?:ate|a partir|todas|todos)\b", text):
        raise ValueError(f"Date label requires a start date or recurrence review: {text}")
    text = text.split("|", 1)[0]
    text = re.sub(r"(?<!\d)\d{1,2}(?:[:h]\d{2}|h)\b", "", text)
    text = re.sub(r"\b(?:segundas?(?:-feiras?)?|tercas?(?:-feiras?)?|quartas?(?:-feiras?)?|quintas?(?:-feiras?)?|sextas?(?:-feiras?)?|sabados?|domingos?|dias?)\b", "", text)
    numeric = list(re.finditer(r"(\d{1,2})[./](\d{1,2})[./](20\d{2})", text))
    if numeric:
        dates = [dt.date(int(m[3]), int(m[2]), int(m[1])) for m in numeric]
        gaps = [text[a.end():b.start()] for a, b in zip(numeric, numeric[1:])]
        ranges = [bool(re.fullmatch(r"\s*(?:-|a)\s*", gap)) for gap in gaps]
        if between:
            if len(dates) != 2 or gaps[0].strip() != "e":
                raise ValueError(f"Ambiguous between-date range: {text}")
            return [(dates[0], dates[-1])]
        if any(re.search(r"\d", gap) for gap in gaps) or (any(ranges) and len(dates) != 2):
            raise ValueError(f"Ambiguous mixture of date ranges and sessions: {text}")
        if ranges and ranges[0]:
            return [(dates[0], dates[-1])]
        return [(date, date) for date in dates]
    pattern = rf"(?<!\d)(\d{{1,2}})\s*(?:de\s+)?({MONTH_RE})(?:\s+(?:de\s+)?(20\d{{2}}))?\b"
    matches = list(re.finditer(pattern, text))
    if not matches:
        raise ValueError(f"Unrecognized date label: {text}")
    dates = [dt.date(int(m[3] or year), MONTHS[m[2]], int(m[1])) for m in matches]
    prefix = re.sub(r"\b20\d{2}\b", "", text[:matches[0].start()]).strip(" ,")
    prefix = re.sub(r"^(?:de|entre)\s+", "", prefix)
    days = re.fullmatch(r"\d{1,2}(?:\s*(?:,|e|a|-)\s*\d{1,2})*\s*(?:,|e|a|-)\s*", prefix)
    if re.search(r"\d", prefix) and days is None:
        raise ValueError(f"Unconsumed session day in date label: {text}")
    if days:
        values = [int(value) for value in re.findall(r"\d{1,2}", days[0])]
        dates = [dt.date(dates[0].year, dates[0].month, day) for day in values] + dates
    gaps = [text[a.end():b.start()] for a, b in zip(matches, matches[1:])]
    if any(re.search(r"\d", gap) for gap in gaps):
        raise ValueError(f"Unconsumed session day in date label: {text}")
    is_range = bool(days and re.search(r"\ba\b|-", prefix)) or any(
        re.fullmatch(r"\s*(?:a|-)\s*", gap) for gap in gaps)
    if between:
        if len(dates) != 2 or not (prefix.endswith("e") or (gaps and gaps[0].strip() == "e")):
            raise ValueError(f"Ambiguous between-date range: {text}")
        is_range = True
    if is_range:
        if len(dates) != 2:
            raise ValueError(f"Ambiguous mixture of date ranges and sessions: {text}")
        start, end = dates[0], dates[-1]
        if end < start and start.month > end.month:
            start = start.replace(year=end.year - 1)
        if end < start:
            raise ValueError(f"Reversed date range: {text}")
        return [(start, end)]
    return [(date, date) for date in dates]


def published_time(text: str) -> str | None:
    """Return a valid 24-hour time explicitly printed in a label or description."""
    text = re.sub(r"</?(?:p|div|br|li)\b[^>]*>", "\n", text)
    for line in text.splitlines():
        line = clean_description(line)
        if re.search(r"duracao|\bdura\b|bilhet|ticketline|ajait|horario.{0,30}(?:funcionamento|atendimento|biblioteca)|segunda.{0,15}sexta|\baberto\b", normalize_name(line)):
            continue
        match = re.search(r"(?<!\d)([01]?\d|2[0-3])(?:\s*:\s*([0-5]\d)|\s*[hH]\s*([0-5]\d)|[hH](?![a-zA-ZÀ-ú\d]))(?!\d)", line)
        if match:
            return f"{int(match[1]):02d}:{match[2] or match[3] or '00'}"
    return None
