"""Session sharing and visibility workflows."""

from __future__ import annotations

from backend.domain.models import SessionRecord
from backend.infrastructure.database.db import now_str, parse_dt
from backend.infrastructure.database.sessions_repo import get_session_by_id, replace_session
from backend.infrastructure.database.users_repo import get_user_by_id


def _require_pending_unlock(session_id: str) -> SessionRecord:
    session = get_session_by_id(session_id)
    if not session or session.visibility != "pending_unlock":
        raise ValueError("session must be pending_unlock")
    return session


def _share_now(session: SessionRecord, now: str | None = None) -> None:
    shared_at = now or now_str()
    session.visibility = "shared"
    session.shared_at = shared_at
    session.unlock_at = shared_at


def can_view_session(session: SessionRecord, viewer_id: str) -> bool:
    if session.user_id == viewer_id:
        return True
    viewer = get_user_by_id(viewer_id)
    if not viewer:
        return False
    if viewer.couple_id != session.couple_id:
        return False
    return session.visibility == "shared"


def request_unlock(session_id: str, unlock_at: str) -> None:
    session = get_session_by_id(session_id)
    if session and session.visibility == "private":
        now = now_str()
        session.unlock_requested_at = now
        unlock_dt = parse_dt(unlock_at)
        now_dt = parse_dt(now)
        if unlock_dt and now_dt and unlock_dt <= now_dt:
            _share_now(session, now)
        else:
            session.unlock_at = unlock_at
            session.visibility = "pending_unlock"
        replace_session(session)


def unlock_now(session_id: str) -> None:
    session = _require_pending_unlock(session_id)
    _share_now(session)
    replace_session(session)


def reschedule_unlock(session_id: str, new_unlock_at: str) -> None:
    session = _require_pending_unlock(session_id)
    new_unlock_dt = parse_dt(new_unlock_at)
    now = now_str()
    now_dt = parse_dt(now)
    if not new_unlock_dt or not now_dt:
        raise ValueError("unlock_at format is invalid")
    if new_unlock_dt <= now_dt:
        _share_now(session, now)
    else:
        session.unlock_at = new_unlock_at
    replace_session(session)


def revoke_unlock(session_id: str) -> None:
    session = get_session_by_id(session_id)
    if session and session.visibility == "pending_unlock":
        session.visibility = "private"
        session.unlock_requested_at = None
        session.unlock_at = None
        replace_session(session)
