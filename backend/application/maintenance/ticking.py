"""State transitions for time locks, frozen couples, and auth token cleanup."""

from __future__ import annotations

from datetime import datetime

from backend.application.sessions.destruction import destroy_couple_data_in_db
from backend.infrastructure.database.db import load_db, now_str, parse_dt, save_db


def tick(db: dict) -> bool:
    now = datetime.now()
    changed = False

    for session in db["sessions"]:
        if session.get("visibility") == "pending_unlock":
            upload_dt = parse_dt(session.get("upload_time", ""))
            if upload_dt and (now - upload_dt).days >= 90:
                session["visibility"] = "shared"
                session["shared_at"] = now_str()
                changed = True

    for couple in db["couples"]:
        if couple.get("couple_status") == "frozen" and couple.get("freeze_ends_at"):
            ends = parse_dt(couple["freeze_ends_at"])
            if ends and now >= ends:
                destroy_couple_data_in_db(db, couple["couple_id"])
                changed = True

    before = len(db.get("auth_tokens", []))
    db["auth_tokens"] = [
        token
        for token in db.get("auth_tokens", [])
        if parse_dt(token.get("expires_at", "")) and parse_dt(token["expires_at"]) > now
    ]
    if len(db["auth_tokens"]) != before:
        changed = True

    return changed


def load_db_with_tick() -> dict:
    db = load_db()
    if tick(db):
        save_db(db)
        db = load_db()
    return db
