"""Low-level SQLite database helpers."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from backend.config.settings import DATA_DIR, DB_PATH, FINAL_DIR, PENDING_DIR

EMPTY_DB: dict = {"users": [], "couples": [], "sessions": [], "auth_tokens": [], "reports": []}

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    couple_id TEXT,
    joined_at TEXT NOT NULL,
    weekly_report_enabled INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS couples (
    couple_id TEXT PRIMARY KEY,
    user_a TEXT NOT NULL,
    user_b TEXT NOT NULL,
    created_at TEXT NOT NULL,
    couple_status TEXT NOT NULL,
    uncouple_initiated_by TEXT,
    uncouple_initiated_at TEXT,
    both_agreed_uncouple INTEGER NOT NULL DEFAULT 0,
    freeze_ends_at TEXT,
    cancel_uncouple_requested_by TEXT,
    cancel_uncouple_requested_at TEXT,
    weekly_report_interval_days INTEGER NOT NULL DEFAULT 7
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    couple_id TEXT,
    status TEXT NOT NULL,
    visibility TEXT NOT NULL,
    unlock_requested_at TEXT,
    unlock_at TEXT,
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

CREATE TABLE IF NOT EXISTS auth_tokens (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    couple_id TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    model_version TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    footprint_json TEXT NOT NULL DEFAULT '{}',
    weather_json TEXT NOT NULL DEFAULT '{}',
    resonance_json TEXT NOT NULL DEFAULT '[]',
    suspense_json TEXT NOT NULL DEFAULT '[]',
    source_session_ids_json TEXT NOT NULL DEFAULT '[]'
);
"""


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _decode_json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []


def _decode_json_dict(value: str | None) -> dict:
    if not value:
        return {}
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _normalize_db(raw: object) -> dict:
    if not isinstance(raw, dict):
        return {key: list(value) for key, value in EMPTY_DB.items()}

    normalized = {key: list(raw.get(key, [])) for key in EMPTY_DB}
    return normalized


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(_SCHEMA)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _migrate_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        _ensure_column(conn, "sessions", "unlock_at", "TEXT")
        _ensure_column(conn, "users", "weekly_report_enabled", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(
            conn,
            "couples",
            "weekly_report_interval_days",
            "INTEGER NOT NULL DEFAULT 7",
        )
        _ensure_column(conn, "couples", "cancel_uncouple_requested_by", "TEXT")
        _ensure_column(conn, "couples", "cancel_uncouple_requested_at", "TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                couple_id TEXT NOT NULL,
                window_start TEXT NOT NULL,
                window_end TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                model_version TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                footprint_json TEXT NOT NULL DEFAULT '{}',
                weather_json TEXT NOT NULL DEFAULT '{}',
                resonance_json TEXT NOT NULL DEFAULT '[]',
                suspense_json TEXT NOT NULL DEFAULT '[]',
                source_session_ids_json TEXT NOT NULL DEFAULT '[]'
            )
            """
        )


def _is_initialized() -> bool:
    return DB_PATH.exists()


def _ensure_ready() -> None:
    if not _is_initialized():
        _init_db()
    _migrate_db()


def _session_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "session_id": row["session_id"],
        "user_id": row["user_id"],
        "couple_id": row["couple_id"],
        "status": row["status"],
        "visibility": row["visibility"],
        "unlock_requested_at": row["unlock_requested_at"],
        "unlock_at": row["unlock_at"],
        "shared_at": row["shared_at"],
        "upload_time": row["upload_time"],
        "archive_time": row["archive_time"],
        "is_complete": bool(row["is_complete"]),
        "edit_history": _decode_json_list(row["edit_history_json"]),
        "files": _decode_json_list(row["files_json"]),
        "source_type": row["source_type"],
        "content_time": row["content_time"],
        "description": row["description"],
        "feeling": row["feeling"],
        "reason": row["reason"],
        "comments": _decode_json_list(row["comments_json"]),
    }


def load_db() -> dict:
    _ensure_ready()
    with _conn() as conn:
        users = [
            {
                "user_id": row["user_id"],
                "username": row["username"],
                "password_hash": row["password_hash"],
                "couple_id": row["couple_id"],
                "joined_at": row["joined_at"],
                "weekly_report_enabled": bool(row["weekly_report_enabled"]),
            }
            for row in conn.execute("SELECT * FROM users ORDER BY joined_at, user_id")
        ]
        couples = [
            {
                "couple_id": row["couple_id"],
                "user_a": row["user_a"],
                "user_b": row["user_b"],
                "created_at": row["created_at"],
                "couple_status": row["couple_status"],
                "uncouple_initiated_by": row["uncouple_initiated_by"],
                "uncouple_initiated_at": row["uncouple_initiated_at"],
                "both_agreed_uncouple": bool(row["both_agreed_uncouple"]),
                "freeze_ends_at": row["freeze_ends_at"],
                "cancel_uncouple_requested_by": row["cancel_uncouple_requested_by"],
                "cancel_uncouple_requested_at": row["cancel_uncouple_requested_at"],
                "weekly_report_interval_days": row["weekly_report_interval_days"],
            }
            for row in conn.execute("SELECT * FROM couples ORDER BY created_at, couple_id")
        ]
        sessions = [
            _session_row_to_dict(row)
            for row in conn.execute("SELECT * FROM sessions ORDER BY upload_time, session_id")
        ]
        auth_tokens = [
            {
                "token": row["token"],
                "user_id": row["user_id"],
                "expires_at": row["expires_at"],
            }
            for row in conn.execute("SELECT * FROM auth_tokens ORDER BY expires_at, token")
        ]
        reports = [
            {
                "report_id": row["report_id"],
                "couple_id": row["couple_id"],
                "window_start": row["window_start"],
                "window_end": row["window_end"],
                "generated_at": row["generated_at"],
                "model_version": row["model_version"],
                "footprint": _decode_json_dict(row["footprint_json"]),
                "weather": _decode_json_dict(row["weather_json"]),
                "resonance": _decode_json_list(row["resonance_json"]),
                "suspense": _decode_json_list(row["suspense_json"]),
                "status": row["status"],
                "source_session_ids": _decode_json_list(row["source_session_ids_json"]),
            }
            for row in conn.execute("SELECT * FROM reports ORDER BY generated_at, report_id")
        ]
    return {
        "users": users,
        "couples": couples,
        "sessions": sessions,
        "auth_tokens": auth_tokens,
        "reports": reports,
    }


def _write_db(normalized: dict) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM auth_tokens")
        conn.execute("DELETE FROM reports")
        conn.execute("DELETE FROM sessions")
        conn.execute("DELETE FROM couples")
        conn.execute("DELETE FROM users")

        conn.executemany(
            """
            INSERT INTO users (
                user_id, username, password_hash, couple_id, joined_at, weekly_report_enabled
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    user["user_id"],
                    user["username"],
                    user["password_hash"],
                    user.get("couple_id"),
                    user["joined_at"],
                    int(bool(user.get("weekly_report_enabled", False))),
                )
                for user in normalized["users"]
            ],
        )
        conn.executemany(
            """
            INSERT INTO couples (
                couple_id, user_a, user_b, created_at, couple_status,
                uncouple_initiated_by, uncouple_initiated_at, both_agreed_uncouple,
                freeze_ends_at, cancel_uncouple_requested_by,
                cancel_uncouple_requested_at, weekly_report_interval_days
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    couple["couple_id"],
                    couple["user_a"],
                    couple["user_b"],
                    couple["created_at"],
                    couple["couple_status"],
                    couple.get("uncouple_initiated_by"),
                    couple.get("uncouple_initiated_at"),
                    int(bool(couple.get("both_agreed_uncouple", False))),
                    couple.get("freeze_ends_at"),
                    couple.get("cancel_uncouple_requested_by"),
                    couple.get("cancel_uncouple_requested_at"),
                    int(couple.get("weekly_report_interval_days", 7)),
                )
                for couple in normalized["couples"]
            ],
        )
        conn.executemany(
            """
            INSERT INTO sessions (
                session_id, user_id, couple_id, status, visibility,
                unlock_requested_at, unlock_at, shared_at, upload_time, archive_time, is_complete,
                source_type, content_time, description, feeling, reason,
                edit_history_json, files_json, comments_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    session["session_id"],
                    session.get("user_id", ""),
                    session.get("couple_id"),
                    session.get("status", "pending"),
                    session.get("visibility", "private"),
                    session.get("unlock_requested_at"),
                    session.get("unlock_at"),
                    session.get("shared_at"),
                    session.get("upload_time", ""),
                    session.get("archive_time", ""),
                    int(bool(session.get("is_complete", False))),
                    session.get("source_type", "file"),
                    session.get("content_time", ""),
                    session.get("description", ""),
                    session.get("feeling", ""),
                    session.get("reason", ""),
                    json.dumps(session.get("edit_history", []), ensure_ascii=False),
                    json.dumps(session.get("files", []), ensure_ascii=False),
                    json.dumps(session.get("comments", []), ensure_ascii=False),
                )
                for session in normalized["sessions"]
            ],
        )
        conn.executemany(
            """
            INSERT INTO auth_tokens (token, user_id, expires_at)
            VALUES (?, ?, ?)
            """,
            [
                (
                    token["token"],
                    token["user_id"],
                    token["expires_at"],
                )
                for token in normalized["auth_tokens"]
            ],
        )
        conn.executemany(
            """
            INSERT INTO reports (
                report_id, couple_id, window_start, window_end, generated_at,
                model_version, status, footprint_json, weather_json, resonance_json,
                suspense_json, source_session_ids_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    report["report_id"],
                    report["couple_id"],
                    report["window_start"],
                    report["window_end"],
                    report["generated_at"],
                    report.get("model_version", ""),
                    report.get("status", "ready"),
                    json.dumps(report.get("footprint", {}), ensure_ascii=False),
                    json.dumps(report.get("weather", {}), ensure_ascii=False),
                    json.dumps(report.get("resonance", []), ensure_ascii=False),
                    json.dumps(report.get("suspense", []), ensure_ascii=False),
                    json.dumps(report.get("source_session_ids", []), ensure_ascii=False),
                )
                for report in normalized["reports"]
            ],
        )


def save_db(data: dict) -> None:
    _ensure_ready()
    _write_db(_normalize_db(data))


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_ready()
