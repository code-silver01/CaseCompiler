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
    with _lock:
        return _store.get(session_id)


def save_session(state: CaseState) -> CaseState:
    """Persist (overwrite) the given state. Updates updated_at timestamp."""
    state.updated_at = _now_iso()
    with _lock:
        _store[state.session_id] = state
    return state


def delete_session(session_id: str) -> bool:
    with _lock:
        if session_id in _store:
            del _store[session_id]
            return True
    return False


def _cleanup_expired() -> None:
    """Remove sessions older than SESSION_TTL_HOURS. Called opportunistically."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=SESSION_TTL_HOURS)
    with _lock:
        expired = [
            sid for sid, state in _store.items()
            if datetime.fromisoformat(state.created_at) < cutoff
        ]
        for sid in expired:
            del _store[sid]
