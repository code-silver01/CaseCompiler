"""
Deterministic date parsing, chronological sorting, and event deduplication.
NO LLM calls here. Uses dateparser + stdlib only.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

import dateparser

from schemas.case_schema import Event


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_DATEPARSER_SETTINGS = {
    "PREFER_DAY_OF_MONTH": "first",
    "RETURN_AS_TIMEZONE_AWARE": False,
    "TIMEZONE": "Asia/Kolkata",
}


def parse_date(raw: str | None) -> Optional[str]:
    """
    Try to parse a raw date string into ISO 8601 (YYYY-MM-DD).
    Returns None if unparseable. Never raises.
    """
    if not raw:
        return None
    raw = raw.strip()
    try:
        parsed: datetime | None = dateparser.parse(raw, settings=_DATEPARSER_SETTINGS)
        if parsed:
            return parsed.date().isoformat()
    except Exception:
        pass
    return None


def days_until(iso_date: str) -> Optional[int]:
    """
    Return number of days from today until iso_date.
    Negative means the date is in the past.
    Returns None if parsing fails.
    """
    try:
        target = date.fromisoformat(iso_date)
        return (target - date.today()).days
    except ValueError:
        return None


def days_since(iso_date: str) -> Optional[int]:
    """Return number of days since iso_date (positive = past)."""
    delta = days_until(iso_date)
    return None if delta is None else -delta


# ---------------------------------------------------------------------------
# Chronological sorting
# ---------------------------------------------------------------------------

def _sort_key(event: Event) -> tuple[int, str]:
    """
    Sort key: events with a parsed date come first (sorted ascending),
    events without a parsed date are pushed to the end sorted by description.
    """
    if event.date_parsed:
        return (0, event.date_parsed)
    return (1, event.description)


def sort_events(events: list[Event]) -> list[Event]:
    """Return a new list sorted chronologically (earliest first)."""
    return sorted(events, key=_sort_key)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.lower().strip())


def deduplicate_events(events: list[Event]) -> list[Event]:
    """
    Remove near-duplicate events based on (date_parsed, normalised description).
    When duplicates exist, prefer the one with higher confidence and a non-null
    parsed date. Preserves order of first occurrence.
    """
    _CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2, "unverified": 3}

    seen: dict[tuple[str, str], Event] = {}
    for ev in events:
        date_key = ev.date_parsed or ""
        desc_key = _normalize(ev.description)
        key = (date_key, desc_key)
        if key not in seen:
            seen[key] = ev
        else:
            existing = seen[key]
            # Prefer higher confidence
            ev_conf = ev.confidence.value if hasattr(ev.confidence, 'value') else ev.confidence
            ex_conf = existing.confidence.value if hasattr(existing.confidence, 'value') else existing.confidence
            if _CONFIDENCE_ORDER.get(ev_conf, 3) < _CONFIDENCE_ORDER.get(ex_conf, 3):
                seen[key] = ev

    return list(seen.values())
