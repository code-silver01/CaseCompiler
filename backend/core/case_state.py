"""
In-memory case state store.
Keyed by session_id (UUID). Sessions expire after SESSION_TTL_HOURS.

FUTURE WORK: Replace with persistent storage (MongoDB, PostgreSQL) for production.
FUTURE WORK: Add encryption-at-rest for case data containing PII.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock

from config import SESSION_TTL_HOURS
from schemas.case_schema import CaseState

_store: dict[str, CaseState] = {}
_lock = Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session() -> CaseState:
    """Create a new blank case session and return it."""
    sid = str(uuid.uuid4())
    now = _now_iso()
    state = CaseState(session_id=sid, created_at=now, updated_at=now)
    with _lock:
        _store[sid] = state
    _cleanup_expired()
    return state


def get_session(session_id: str) -> CaseState | None:
    """Retrieve an active case state by session ID, or None if expired/not found."""
    with _lock:
        return _store.get(session_id)


def save_session(state: CaseState) -> CaseState:
    """Persist (overwrite) the given state. Updates updated_at timestamp."""
    state.updated_at = _now_iso()
    with _lock:
        _store[state.session_id] = state
    return state


def delete_session(session_id: str) -> bool:
    """Remove a case session from the in-memory store. Returns True if deleted."""
    with _lock:
        if session_id in _store:
            del _store[session_id]
            return True
    return False


def _cleanup_expired() -> None:
    """Remove sessions older than SESSION_TTL_HOURS. Called opportunistically."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=SESSION_TTL_HOURS)
    with _lock:
        expired = []
        for sid, state in list(_store.items()):
            try:
                dt = datetime.fromisoformat(state.created_at)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt < cutoff:
                    expired.append(sid)
            except Exception:
                pass
        for sid in expired:
            _store.pop(sid, None)
