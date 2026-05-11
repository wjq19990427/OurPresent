from __future__ import annotations

import sqlite3

from backend.domain.models import AuthToken, Couple, SessionRecord, User
from backend.infrastructure.database import db as db_module


def test_domain_models_round_trip() -> None:
    user = User("usr_1", "alice", "hash", None, "2026-05-01 10:00:00")
    couple = Couple(
        "cp_1",
        "usr_1",
        "usr_2",
        "2026-05-01 10:00:00",
        "active",
        None,
        None,
        False,
        None,
    )
    session = SessionRecord(
        session_id="sess_1",
        user_id="usr_1",
        couple_id="cp_1",
        status="final",
        visibility="shared",
        unlock_requested_at=None,
        unlock_at=None,
        shared_at="2026-05-01 12:00:00",
        upload_time="2026-05-01 10:00:00",
        archive_time="2026-05-01 11:00:00",
        is_complete=True,
        files=[{"filename": "a.txt", "path": "/tmp/a.txt", "original_name": "a.txt"}],
        comments=[{"id": "1", "text": "hi", "created_at": "2026-05-01 12:00:00"}],
    )
    token = AuthToken("token", "usr_1", "2026-05-02 10:00:00")

    assert User.from_dict(user.to_dict()) == user
    assert Couple.from_dict(couple.to_dict()) == couple
    assert SessionRecord.from_dict(session.to_dict()) == session
    assert SessionRecord.from_dict({**session.to_dict(), "unlock_at": ""}).unlock_at is None
    assert AuthToken.from_dict(token.to_dict()) == token


def test_load_db_returns_empty_when_missing() -> None:
    assert db_module.load_db() == db_module.EMPTY_DB


def test_save_db_and_ensure_dirs_persist_data() -> None:
    payload = {
        "users": [
            {
                "user_id": "usr_1",
                "username": "alice",
                "password_hash": "hash",
                "couple_id": None,
                "joined_at": "2026-05-01 10:00:00",
            }
        ],
        "couples": [],
        "sessions": [],
        "auth_tokens": [],
    }

    db_module.ensure_dirs()
    db_module.save_db(payload)

    assert db_module.DATA_DIR.exists()
    assert db_module.PENDING_DIR.exists()
    assert db_module.FINAL_DIR.exists()
    assert db_module.load_db() == payload
    with sqlite3.connect(db_module.DB_PATH) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    assert {"users", "couples", "sessions", "auth_tokens"} <= tables


def test_parse_dt_handles_blank_and_invalid_values() -> None:
    assert db_module.parse_dt("") is None
    assert db_module.parse_dt("not-a-date") is None
    assert db_module.parse_dt("2026-05-01 10:00:00") is not None
