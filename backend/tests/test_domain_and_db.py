from __future__ import annotations

import sqlite3

from backend.domain.models import AuthToken, Couple, Report, SessionRecord, User
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
    report = Report(
        report_id="rpt_20260510_cp_1",
        couple_id="cp_1",
        window_start="2026-05-04 00:00:00",
        window_end="2026-05-10 23:59:59",
        generated_at="2026-05-11 03:00:00",
        model_version="",
        footprint={"total": 1},
        weather={"narrative": "晴"},
        resonance=[{"day": "2026-05-06"}],
        suspense=[{"session_id": "sess_1"}],
        status="ready",
        source_session_ids=["sess_1"],
    )

    assert User.from_dict(user.to_dict()) == user
    assert Couple.from_dict(couple.to_dict()) == couple
    assert SessionRecord.from_dict(session.to_dict()) == session
    assert SessionRecord.from_dict({**session.to_dict(), "unlock_at": ""}).unlock_at is None
    assert AuthToken.from_dict(token.to_dict()) == token
    assert Report.from_dict(report.to_dict()) == report
    assert User.from_dict({**user.to_dict(), "weekly_report_enabled": 1}).weekly_report_enabled
    migrated_couple = Couple.from_dict({**couple.to_dict(), "weekly_report_interval_days": 14})
    assert migrated_couple.weekly_report_interval_days == 14


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
                "weekly_report_enabled": False,
            }
        ],
        "couples": [],
        "sessions": [],
        "auth_tokens": [],
        "reports": [],
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
    assert {"users", "couples", "sessions", "auth_tokens", "reports"} <= tables


def test_old_sqlite_schema_migrates_new_report_fields() -> None:
    db_module.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_module.DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                couple_id TEXT,
                joined_at TEXT NOT NULL
            );
            CREATE TABLE couples (
                couple_id TEXT PRIMARY KEY,
                user_a TEXT NOT NULL,
                user_b TEXT NOT NULL,
                created_at TEXT NOT NULL,
                couple_status TEXT NOT NULL,
                uncouple_initiated_by TEXT,
                uncouple_initiated_at TEXT,
                both_agreed_uncouple INTEGER NOT NULL DEFAULT 0,
                freeze_ends_at TEXT
            );
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                couple_id TEXT,
                status TEXT NOT NULL,
                visibility TEXT NOT NULL,
                unlock_requested_at TEXT,
                shared_at TEXT,
                upload_time TEXT NOT NULL,
                archive_time TEXT NOT NULL,
                is_complete INTEGER NOT NULL DEFAULT 0,
                source_type TEXT NOT NULL DEFAULT 'file',
                content_time TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                feeling TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                edit_history_json TEXT NOT NULL DEFAULT '[]',
                files_json TEXT NOT NULL DEFAULT '[]',
                comments_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE auth_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            INSERT INTO users (user_id, username, password_hash, couple_id, joined_at)
            VALUES ('usr_1', 'alice', 'hash', NULL, '2026-05-01 10:00:00');
            INSERT INTO couples (
                couple_id, user_a, user_b, created_at, couple_status,
                uncouple_initiated_by, uncouple_initiated_at, both_agreed_uncouple, freeze_ends_at
            )
            VALUES (
                'cp_1', 'usr_1', 'usr_2', '2026-05-01 10:00:00',
                'active', NULL, NULL, 0, NULL
            );
            """
        )

    loaded = db_module.load_db()

    assert loaded["reports"] == []
    assert loaded["users"][0]["weekly_report_enabled"] is False
    assert loaded["couples"][0]["weekly_report_interval_days"] == 7

    db_module.save_db(loaded)
    assert db_module.load_db() == loaded


def test_parse_dt_handles_blank_and_invalid_values() -> None:
    assert db_module.parse_dt("") is None
    assert db_module.parse_dt("not-a-date") is None
    assert db_module.parse_dt("2026-05-01 10:00:00") is not None
