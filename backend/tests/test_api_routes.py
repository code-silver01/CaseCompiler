"""
Integration tests for CaseCompiler FastAPI endpoints.
Tests run completely offline using FastAPI TestClient with no external API calls.
"""
import io
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root_endpoint():
    """GET / should return 200 with online status and service metadata."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "CaseCompiler" in data["service"]


def test_owasp_security_headers_present():
    """All responses must include OWASP defensive security headers."""
    res = client.get("/")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert "strict-origin" in res.headers.get("Referrer-Policy", "")


def test_health_endpoint():
    """GET /api/health should return 200 and report active model names."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "model" in data


def test_session_lifecycle():
    """Verify session creation, retrieval, phase check, and deletion."""
    # 1. Create session
    create_res = client.post("/api/session")
    assert create_res.status_code == 200
    data = create_res.json()
    session_id = data["session_id"]
    assert session_id

    # 2. Get active session state
    get_res = client.get(f"/api/session/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["session_id"] == session_id

    # 3. Check phase endpoint
    phase_res = client.get(f"/api/session/{session_id}/phase")
    assert phase_res.status_code == 200
    assert "phase" in phase_res.json()

    # 4. Delete session
    del_res = client.delete(f"/api/session/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 5. Verify deleted session returns 404
    get_deleted = client.get(f"/api/session/{session_id}")
    assert get_deleted.status_code == 404


def test_invalid_session_id_format():
    """Invalid session IDs containing malicious characters or path traversal should return 400."""
    res = client.get("/api/session/../../etc/passwd")
    # Starlette routing or regex validation returns 400 or 404
    assert res.status_code in (400, 404)

    bad_id = client.get("/api/session/invalid!@#$%^&*")
    assert bad_id.status_code in (400, 404)


def test_extract_rejects_empty_description():
    """POST /extract without a description or with whitespace should return 400."""
    create_res = client.post("/api/session")
    session_id = create_res.json()["session_id"]

    res = client.post(
        f"/api/session/{session_id}/extract",
        data={"description": "   "},
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def test_extract_rejects_unauthorized_file_extension():
    """POST /extract with executable or dangerous extensions (.exe, .sh) should return 400."""
    create_res = client.post("/api/session")
    session_id = create_res.json()["session_id"]

    fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00")
    res = client.post(
        f"/api/session/{session_id}/extract",
        data={"description": "Valid dispute description with bad attachment."},
        files={"files": ("malware.exe", fake_exe, "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "unsupported format" in res.json()["detail"].lower()


def test_extract_rejects_spoofed_magic_bytes():
    """POST /extract with .pdf extension containing non-PDF binary data should be rejected with 400."""
    create_res = client.post("/api/session")
    session_id = create_res.json()["session_id"]

    fake_pdf = io.BytesIO(b"NOT_A_REAL_PDF_HEADER_JUST_RANDOM_TEXT")
    res = client.post(
        f"/api/session/{session_id}/extract",
        data={"description": "My landlord withheld my security deposit."},
        files={"files": ("disguised_script.pdf", fake_pdf, "application/pdf")},
    )
    assert res.status_code == 400
    assert "contents do not match" in res.json()["detail"].lower()
