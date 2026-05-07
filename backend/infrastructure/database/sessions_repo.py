"""Session repository backed by the local JSON database."""

from __future__ import annotations

from backend.domain.models import SessionRecord
from backend.infrastructure.database.db import load_db, save_db


def add_session(session: SessionRecord) -> None:
    db = load_db()
    db["sessions"].append(session.to_dict())
    save_db(db)


def list_sessions() -> list[SessionRecord]:
    db = load_db()
    return [SessionRecord.from_dict(raw_session) for raw_session in db["sessions"]]


def get_session_by_id(session_id: str) -> SessionRecord | None:
    db = load_db()
    for raw_session in db["sessions"]:
        if raw_session["session_id"] == session_id:
            return SessionRecord.from_dict(raw_session)
    return None


def replace_session(session: SessionRecord) -> None:
    db = load_db()
    for index, raw_session in enumerate(db["sessions"]):
        if raw_session["session_id"] == session.session_id:
            db["sessions"][index] = session.to_dict()
            break
    save_db(db)


def list_sessions_for_user(user_id: str) -> list[SessionRecord]:
    return [session for session in list_sessions() if session.user_id == user_id]
