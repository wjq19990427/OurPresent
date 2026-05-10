"""Session cleanup workflows."""

from __future__ import annotations

from pathlib import Path

from backend.config import settings
from backend.infrastructure.database.db import load_db, save_db


def _delete_session_files(session_id: str, files: list[dict]) -> None:
    for file_record in files:
        path = Path(file_record.get("path", ""))
        if path.exists():
            path.unlink(missing_ok=True)
    (settings.FINAL_DIR / f"{session_id}.md").unlink(missing_ok=True)


def destroy_couple_data_in_db(db: dict, couple_id: str) -> None:
    to_remove = [session for session in db["sessions"] if session.get("couple_id") == couple_id]
    for session in to_remove:
        _delete_session_files(session["session_id"], session.get("files", []))
    db["sessions"] = [
        session for session in db["sessions"] if session.get("couple_id") != couple_id
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
