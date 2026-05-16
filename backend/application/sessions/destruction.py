"""Session cleanup workflows."""

from __future__ import annotations

from backend.application.sessions.files import delete_session_files
from backend.domain.models import SessionRecord
from backend.infrastructure.database.db import load_db, save_db
from backend.infrastructure.database.sessions_repo import get_session_by_id


def delete_session(session_id: str, user_id: str) -> None:
    session = get_session_by_id(session_id)
    if not session:
        raise ValueError("记录不存在。")
    if session.user_id != user_id:
        raise ValueError("只能删除自己的记录。")
    if session.visibility == "shared":
        raise ValueError("已共享的记录不能在这里删除。")

    delete_session_files(session)

    db = load_db()
    db["sessions"] = [
        raw_session
        for raw_session in db["sessions"]
        if raw_session.get("session_id") != session_id
    ]
    save_db(db)


def destroy_couple_data_in_db(db: dict, couple_id: str) -> None:
    to_remove = [session for session in db["sessions"] if session.get("couple_id") == couple_id]
    for session in to_remove:
        delete_session_files(SessionRecord.from_dict(session))
    db["sessions"] = [
        session for session in db["sessions"] if session.get("couple_id") != couple_id
    ]
    db["reports"] = [
        report for report in db.get("reports", []) if report.get("couple_id") != couple_id
    ]
    for couple in db["couples"]:
        if couple["couple_id"] == couple_id:
            couple["couple_status"] = "dissolved"
    for user in db["users"]:
        if user.get("couple_id") == couple_id:
            user["couple_id"] = None


def destroy_couple_data(couple_id: str) -> None:
    db = load_db()
    destroy_couple_data_in_db(db, couple_id)
    save_db(db)
