"""
Unit tests for pure, non-LLM functions in LegalAI backend.
These tests run instantly and offline without any network or Gemini API calls.
"""
from datetime import date, timedelta
import pytest

from core.triage import compute_triage
from core.chronology import parse_date, sort_events, deduplicate_events
from schemas.case_schema import (
    CaseState,
    Event,
    FieldSource,
    SourceType,
    ConfidenceLevel,
)


def _make_source() -> FieldSource:
    return FieldSource(type=SourceType.USER_STATEMENT, reference="test input")


# ---------------------------------------------------------------------------
# Tests for triage.py: compute_triage()
# ---------------------------------------------------------------------------

def test_compute_triage_court_date_within_7_days_high():
    """A court hearing date within 7 days must be triaged as HIGH urgency."""
    target_date = (date.today() + timedelta(days=5)).isoformat()
    court_event = Event(
        date_raw="in 5 days",
        date_parsed=target_date,
        description="Court hearing before the Small Causes Court regarding eviction petition",
        source=_make_source(),
        confidence=ConfidenceLevel.HIGH,
    )
    state = CaseState(
        session_id="test-session-high",
        created_at=date.today().isoformat(),
        updated_at=date.today().isoformat(),
        events=[court_event],
    )

    triage = compute_triage(state)
    assert triage.level == "HIGH"
    assert triage.score >= 70
    assert any("Court/tribunal date" in r for r in triage.reasons)


def test_compute_triage_no_urgency_low():
    """A case with past routine events and no critical keywords should be LOW urgency."""
    past_date = (date.today() - timedelta(days=60)).isoformat()
    routine_event = Event(
        date_raw="two months ago",
        date_parsed=past_date,
        description="Signed lease agreement and moved furniture into the apartment",
        source=_make_source(),
        confidence=ConfidenceLevel.MEDIUM,
    )
    state = CaseState(
        session_id="test-session-low",
        created_at=date.today().isoformat(),
        updated_at=date.today().isoformat(),
        events=[routine_event],
    )

    triage = compute_triage(state)
    assert triage.level == "LOW"
    assert triage.score < 40
    assert len(triage.reasons) > 0


# ---------------------------------------------------------------------------
# Tests for chronology.py: parse_date(), sort_events(), deduplicate_events()
# ---------------------------------------------------------------------------

def test_parse_date_valid_and_unparseable():
    """parse_date returns ISO 8601 string for valid dates and None for unparseable strings."""
    assert parse_date("15 August 2024") == "2024-08-15"
    assert parse_date("2024-01-31") == "2024-01-31"

    # Unparseable strings and edge cases
    assert parse_date("not a real date string 12345 xyz") is None
    assert parse_date("") is None
    assert parse_date(None) is None


def test_sort_events_chronological_order():
    """sort_events orders earliest date first, and places unparsed dates at the end."""
    e1 = Event(
        date_parsed="2024-05-01",
        description="Notice sent",
        source=_make_source(),
        confidence=ConfidenceLevel.HIGH,
    )
    e2 = Event(
        date_parsed="2023-01-10",
        description="Lease commenced",
        source=_make_source(),
        confidence=ConfidenceLevel.HIGH,
    )
    e3 = Event(
        date_parsed=None,
        description="Informal discussion over telephone",
        source=_make_source(),
        confidence=ConfidenceLevel.LOW,
    )

    sorted_list = sort_events([e1, e3, e2])
    assert sorted_list[0].date_parsed == "2023-01-10"
    assert sorted_list[1].date_parsed == "2024-05-01"
    assert sorted_list[2].date_parsed is None


def test_deduplicate_events_near_duplicates_merge():
    """deduplicate_events removes duplicate events with same date and normalized description, preferring higher confidence."""
    e_low = Event(
        date_parsed="2024-02-15",
        description="Vacated the flat and handed over keys",
        source=_make_source(),
        confidence=ConfidenceLevel.LOW,
    )
    e_high = Event(
        date_parsed="2024-02-15",
        description="  vacated the flat and handed over keys   ",
        source=_make_source(),
        confidence=ConfidenceLevel.HIGH,
    )
    e_different = Event(
        date_parsed="2024-02-20",
        description="Sent email follow up for deposit",
        source=_make_source(),
        confidence=ConfidenceLevel.HIGH,
    )

    deduped = deduplicate_events([e_low, e_high, e_different])
    assert len(deduped) == 2
    # The duplicate for 2024-02-15 should keep the HIGH confidence event
    vacated_ev = next(e for e in deduped if e.date_parsed == "2024-02-15")
    assert vacated_ev.confidence == ConfidenceLevel.HIGH


# ---------------------------------------------------------------------------
# Tests for routes.py: _validate_upload()
# ---------------------------------------------------------------------------

def test_validate_upload_allowed_and_rejected():
    """_validate_upload accepts pdf/jpg/jpeg/png under 10MB, and rejects invalid types or oversize files with 400."""
    import io
    from fastapi import UploadFile, HTTPException
    from api.routes import _validate_upload

    # 1. Valid PDF file (with %PDF- magic bytes)
    valid_pdf = UploadFile(filename="agreement.pdf", file=io.BytesIO(b"%PDF-1.4 valid pdf content"))
    _validate_upload(valid_pdf)  # should not raise

    # 2. Valid image files (with PNG magic bytes)
    valid_png = UploadFile(filename="receipt.png", file=io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR valid png"))
    _validate_upload(valid_png)  # should not raise

    # 3. Disallowed file extension (.exe, .zip, .docx)
    invalid_ext = UploadFile(filename="malicious.exe", file=io.BytesIO(b"bad content"))
    with pytest.raises(HTTPException) as exc_info:
        _validate_upload(invalid_ext)
    assert exc_info.value.status_code == 400
    assert "unsupported format" in exc_info.value.detail.lower()

    # 4. File over 10MB
    oversize_bytes = io.BytesIO(b"%PDF-" + b"0" * (10 * 1024 * 1024 + 1024))
    oversize_file = UploadFile(filename="large_scan.pdf", file=oversize_bytes)
    with pytest.raises(HTTPException) as exc_info_size:
        _validate_upload(oversize_file)
    assert exc_info_size.value.status_code == 400
    assert "exceeds maximum allowed size" in exc_info_size.value.detail.lower()

    # 5. Spoofed file: .pdf extension with non-PDF text/binary content
    spoofed_file = UploadFile(filename="spoofed.pdf", file=io.BytesIO(b"<html>malicious payload</html>"))
    with pytest.raises(HTTPException) as exc_spoof:
        _validate_upload(spoofed_file)
    assert exc_spoof.value.status_code == 400
    assert "binary signature" in exc_spoof.value.detail.lower()
