"""Replay a synth script through backend application services."""

from __future__ import annotations

import os
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

TIME_FMT = "%Y-%m-%d %H:%M:%S"


class SynthConfigError(ValueError):
    """Raised when synth storage isolation is unsafe."""


class SynthClock:
    def __init__(self, current: str) -> None:
        self.current = datetime.strptime(current, TIME_FMT)

    def set(self, value: str) -> None:
        self.current = datetime.strptime(value, TIME_FMT)

    def now(self) -> datetime:
        return self.current

    def now_str(self) -> str:
        return self.current.strftime(TIME_FMT)


def run_script(script: dict[str, Any], reset_db: bool = True) -> Path:
    return run_scripts([script], reset_db=reset_db)


def run_scripts(scripts: list[dict[str, Any]], reset_db: bool = True) -> Path:
    if not scripts:
        raise ValueError("at least one synth script is required")
    db_path, assets_root = validate_synth_storage()
    if reset_db:
        reset_synth_storage(db_path, assets_root)

    with patched_backend(db_path, assets_root, scripts[0]["metadata"]["generated_at"]) as clock:
        for script in scripts:
            _run_script_body(script, clock)

    return db_path


def _run_script_body(script: dict[str, Any], clock: SynthClock) -> None:
    from backend.application.auth import register
    from backend.application.couples import accept_bind, send_bind_request, start_uncouple
    from backend.application.sessions import (
        add_comment,
        destroy_couple_data,
        request_unlock,
        reschedule_unlock,
        save_session_final,
        unlock_now,
    )

    user_ids: dict[str, str] = {}
    couple_ids: dict[str, str] = {}
    for couple in script["couples"]:
        clock.set(script["metadata"]["generated_at"])
        user_a = register(couple["a"]["username"], couple["password"])
        user_b = register(couple["b"]["username"], couple["password"])
        bind = send_bind_request(user_a.user_id, user_b.user_id)
        accept_bind(bind.couple_id)
        user_ids[f"{couple['ref']}:A"] = user_a.user_id
        user_ids[f"{couple['ref']}:B"] = user_b.user_id
        couple_ids[couple["ref"]] = bind.couple_id

    for session in script["sessions"]:
        clock.set(session["created_at"])
        created_at = datetime.strptime(session["created_at"], TIME_FMT)
        session_id = created_at.strftime("%Y%m%d_%H%M%S")
        couple_ref = session["couple_ref"]
        save_session_final(
            user_ids[f"{couple_ref}:{session['author']}"],
            couple_ids[couple_ref],
            [],
            session["source_type"],
            session["fields"],
        )
        for action in session.get("actions", []):
            clock.set(action["at"])
            if action["type"] == "request_unlock":
                request_unlock(session_id, action["unlock_at"])
            elif action["type"] == "reschedule_unlock":
                reschedule_unlock(session_id, action["unlock_at"])
            elif action["type"] == "unlock_now":
                unlock_now(session_id)
            elif action["type"] == "add_comment":
                author_id = user_ids[f"{couple_ref}:{action['author']}"]
                add_comment(session_id, author_id, action["text"])
            else:
                raise ValueError(f"unsupported session action: {action['type']}")

    for action in script.get("destroy_actions", []):
        couple_ref = action["couple_ref"]
        clock.set(action["start_uncouple_at"])
        start_uncouple(user_ids[f"{couple_ref}:{action['initiator']}"])
        clock.set(action["destroy_at"])
        destroy_couple_data(couple_ids[couple_ref])


def validate_synth_storage() -> tuple[Path, Path]:
    from backend.config import settings

    raw_path = os.getenv("SYNTH_DB_PATH", "").strip()
    if not raw_path:
        raise SynthConfigError("SYNTH_DB_PATH must be set for synth runs")
    db_path = Path(raw_path).expanduser()
    if not db_path.is_absolute():
        db_path = settings.BASE_DIR / db_path
    db_path = db_path.resolve()

    production_db = settings.DB_PATH.resolve()
    if db_path == production_db:
        raise SynthConfigError("SYNTH_DB_PATH must not point to data/database.db")

    parent = db_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    if not os.access(parent, os.W_OK):
        raise SynthConfigError(f"SYNTH_DB_PATH parent is not writable: {parent}")

    raw_assets = os.getenv("SYNTH_ASSETS_ROOT", "").strip()
    if raw_assets:
        assets_root = Path(raw_assets).expanduser()
        if not assets_root.is_absolute():
            assets_root = settings.BASE_DIR / assets_root
    else:
        assets_root = parent.parent / "Assets"
    assets_root = assets_root.resolve()
    if assets_root == settings.ASSETS_DIR.resolve():
        raise SynthConfigError("SYNTH_ASSETS_ROOT must not point to production Assets/")
    return db_path, assets_root


def reset_synth_storage(db_path: Path, assets_root: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(f"{db_path}{suffix}")
        if candidate.exists():
            candidate.unlink()
    if assets_root.exists():
        shutil.rmtree(assets_root)


@contextmanager
def patched_backend(db_path: Path, assets_root: Path, initial_time: str) -> Iterator[SynthClock]:
    from backend.application.couples import uncoupling
    from backend.application.sessions import comments, creation, editing, files, markdown, sharing
    from backend.config import settings
    from backend.infrastructure.database import couples_repo, users_repo
    from backend.infrastructure.database import db as db_module

    clock = SynthClock(initial_time)
    data_dir = db_path.parent
    pending_dir = assets_root / "Pending"
    final_dir = assets_root / "Final"
    for path in (data_dir, pending_dir, final_dir):
        path.mkdir(parents=True, exist_ok=True)

    patches = [
        (settings, "DATA_DIR", data_dir),
        (settings, "DB_PATH", db_path),
        (settings, "ASSETS_DIR", assets_root),
        (settings, "PENDING_DIR", pending_dir),
        (settings, "FINAL_DIR", final_dir),
        (db_module, "DATA_DIR", data_dir),
        (db_module, "DB_PATH", db_path),
        (db_module, "PENDING_DIR", pending_dir),
        (db_module, "FINAL_DIR", final_dir),
        (db_module, "now_str", clock.now_str),
        (users_repo, "now_str", clock.now_str),
        (couples_repo, "now_str", clock.now_str),
        (creation, "datetime", clock),
        (creation, "now_str", clock.now_str),
        (creation, "PENDING_DIR", pending_dir),
        (creation, "FINAL_DIR", final_dir),
        (editing, "FINAL_DIR", final_dir),
        (files, "FINAL_DIR", final_dir),
        (markdown, "FINAL_DIR", final_dir),
        (comments, "datetime", clock),
        (sharing, "now_str", clock.now_str),
        (uncoupling, "datetime", clock),
        (uncoupling, "now_str", clock.now_str),
    ]
    originals = [(module, name, getattr(module, name)) for module, name, _ in patches]
    uuid_original = uuid.uuid4
    gensalt_original = users_repo.bcrypt.gensalt
    uuid_values = _uuid_sequence()

    try:
        for module, name, value in patches:
            setattr(module, name, value)
        uuid.uuid4 = lambda: next(uuid_values)  # type: ignore[method-assign]
        users_repo.bcrypt.gensalt = lambda: b"$2b$12$abcdefghijklmnopqrstuu"
        yield clock
    finally:
        for module, name, value in originals:
            setattr(module, name, value)
        uuid.uuid4 = uuid_original  # type: ignore[method-assign]
        users_repo.bcrypt.gensalt = gensalt_original


def summarize_sqlite(db_path: Path) -> dict[str, int]:
    with sqlite3.connect(db_path) as conn:
        return {
            "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "couples": conn.execute("SELECT COUNT(*) FROM couples").fetchone()[0],
            "sessions": conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
            "shared_sessions": conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE visibility = 'shared'"
            ).fetchone()[0],
            "pending_unlock_sessions": conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE visibility = 'pending_unlock'"
            ).fetchone()[0],
            "private_sessions": conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE visibility = 'private'"
            ).fetchone()[0],
            "dissolved_couples": conn.execute(
                "SELECT COUNT(*) FROM couples WHERE couple_status = 'dissolved'"
            ).fetchone()[0],
        }


def _uuid_sequence() -> Iterator[uuid.UUID]:
    index = 1
    while True:
        yield uuid.UUID(hex=f"{index:08x}{0:024x}")
        index += 1
