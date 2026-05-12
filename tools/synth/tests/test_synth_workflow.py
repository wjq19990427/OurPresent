from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tools.synth.actions import build_script
from tools.synth.driver import SynthConfigError, run_script, validate_synth_storage
from tools.synth.persona import load_persona_seed
from tools.synth.timeline import deterministic_timeline


def _script() -> dict:
    seed = load_persona_seed()
    timeline = deterministic_timeline(seed, weeks=6)
    return build_script(seed, timeline, weeks=6)


def test_replay_writes_expected_distribution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "synth" / "data" / "database.db"
    monkeypatch.setenv("SYNTH_DB_PATH", str(db_path))

    run_script(_script())

    with sqlite3.connect(db_path) as conn:
        visibility = dict(
            conn.execute("SELECT visibility, COUNT(*) FROM sessions GROUP BY visibility").fetchall()
        )
        comments = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE comments_json != '[]'"
        ).fetchone()[0]
        dissolved = conn.execute(
            "SELECT COUNT(*) FROM couples WHERE couple_status = 'dissolved'"
        ).fetchone()[0]
        destroyed_leftovers = conn.execute(
            """
            SELECT COUNT(*)
            FROM sessions
            WHERE couple_id IN (
                SELECT couple_id FROM couples WHERE couple_status = 'dissolved'
            )
            """
        ).fetchone()[0]

    assert visibility == {"pending_unlock": 4, "private": 1, "shared": 1}
    assert comments == 1
    assert dissolved == 1
    assert destroyed_leftovers == 0


def test_replay_is_stable_after_reset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "synth" / "data" / "database.db"
    monkeypatch.setenv("SYNTH_DB_PATH", str(db_path))
    script = _script()

    run_script(script)
    first_summary = _dump_tables(db_path)
    run_script(script)
    second_summary = _dump_tables(db_path)

    assert first_summary == second_summary


def test_rejects_production_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYNTH_DB_PATH", "data/database.db")

    with pytest.raises(SynthConfigError, match="data/database.db"):
        validate_synth_storage()


def _dump_tables(db_path: Path) -> dict[str, list[tuple]]:
    with sqlite3.connect(db_path) as conn:
        return {
            "users": conn.execute("SELECT * FROM users ORDER BY user_id").fetchall(),
            "couples": conn.execute("SELECT * FROM couples ORDER BY couple_id").fetchall(),
            "sessions": conn.execute("SELECT * FROM sessions ORDER BY session_id").fetchall(),
        }
