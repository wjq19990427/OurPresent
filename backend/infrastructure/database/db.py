"""Low-level JSON database access helpers."""

from __future__ import annotations

import json
from datetime import datetime

from backend.config.settings import DATA_DIR, DB_PATH, FINAL_DIR, PENDING_DIR

EMPTY_DB: dict = {"users": [], "couples": [], "sessions": [], "auth_tokens": []}


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def load_db() -> dict:
    if not DB_PATH.exists():
        return {key: list(value) for key, value in EMPTY_DB.items()}
    try:
        raw = json.loads(DB_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return {"users": [], "couples": [], "sessions": raw, "auth_tokens": []}
        if "auth_tokens" not in raw:
            raw["auth_tokens"] = []
        return raw
    except (json.JSONDecodeError, OSError):
        return {key: list(value) for key, value in EMPTY_DB.items()}


def save_db(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
