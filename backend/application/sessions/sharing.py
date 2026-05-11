"""Session sharing and visibility workflows."""

from __future__ import annotations

from backend.domain.models import SessionRecord
from backend.infrastructure.database.db import now_str, parse_dt
from backend.infrastructure.database.sessions_repo import get_session_by_id, replace_session
from backend.infrastructure.database.users_repo import get_user_by_id


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
        session.unlock_at = unlock_at
        unlock_dt = parse_dt(unlock_at)
        now_dt = parse_dt(now)
        if unlock_dt and now_dt and unlock_dt <= now_dt:
            session.visibility = "shared"
            session.shared_at = now
        else:
            session.visibility = "pending_unlock"
        replace_session(session)


def revoke_unlock(session_id: str) -> None:
    session = get_session_by_id(session_id)
    if session and session.visibility == "pending_unlock":
        session.visibility = "private"
        session.unlock_requested_at = None
        session.unlock_at = None
        replace_session(session)
