"""OAI datestamp normalization and from/until filtering."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SECONDS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_YEAR = re.compile(r"^\d{4}$")


def normalize_datestamp(raw: str | None) -> str:
    """Coerce a VOResource ``@updated`` value to ``YYYY-MM-DDThh:mm:ssZ``."""
    if not raw or not raw.strip():
        return "2000-01-01T00:00:00Z"
    text = raw.strip()
    if _SECONDS.match(text):
        return text
    if _DAY.match(text):
        return f"{text}T00:00:00Z"
    if text.endswith("Z") and "T" in text:
        base = text.split(".", 1)[0]
        if base.endswith("Z"):
            base = base[:-1]
        try:
            dt = datetime.fromisoformat(base).replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass
    if "T" in text:
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass
    return f"{text}T00:00:00Z" if _DAY.match(text[:10]) else "2000-01-01T00:00:00Z"


@dataclass(frozen=True)
class ParsedOaiDate:
    raw: str
    granularity: str  # "day" or "seconds"
    instant: datetime


def parse_oai_date(value: str) -> ParsedOaiDate | None:
    """Parse an OAI ``from``/``until`` argument."""
    text = value.strip()
    if _YEAR.match(text):
        return None
    if _DAY.match(text):
        dt = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return ParsedOaiDate(raw=text, granularity="day", instant=dt)
    if _SECONDS.match(text):
        dt = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return ParsedOaiDate(raw=text, granularity="seconds", instant=dt)
    return None


def validate_from_until(
    from_raw: str | None,
    until_raw: str | None,
) -> str | None:
    """Return an OAI error code when ``from``/``until`` are invalid, else ``None``."""
    if from_raw is None and until_raw is None:
        return None

    from_parsed: ParsedOaiDate | None = None
    until_parsed: ParsedOaiDate | None = None

    if from_raw is not None:
        if from_raw.strip() and _SECONDS.match(from_raw.strip()):
            return "badArgument"
        from_parsed = parse_oai_date(from_raw)
        if from_parsed is None:
            return "badArgument"

    if until_raw is not None:
        until_parsed = parse_oai_date(until_raw)
        if until_parsed is None:
            return "badArgument"

    if from_parsed and until_parsed:
        if from_parsed.granularity != until_parsed.granularity:
            return "badArgument"
        if from_parsed.instant > until_parsed.instant:
            return "badArgument"

    return None


def record_in_range(datestamp: str, from_raw: str | None, until_raw: str | None) -> bool:
    """Return whether ``datestamp`` falls within optional ``from``/``until`` bounds."""
    rec = datetime.strptime(normalize_datestamp(datestamp), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if from_raw is not None:
        fp = parse_oai_date(from_raw)
        if fp is None:
            return False
        if fp.granularity == "day":
            if rec.date() < fp.instant.date():
                return False
        elif rec < fp.instant:
            return False
    if until_raw is not None:
        up = parse_oai_date(until_raw)
        if up is None:
            return False
        if up.granularity == "day":
            if rec.date() > up.instant.date():
                return False
        elif rec > up.instant:
            return False
    return True


def earliest_datestamp(datestamps: list[str]) -> str:
    if not datestamps:
        return "2000-01-01T00:00:00Z"
    return min(normalize_datestamp(d) for d in datestamps)
