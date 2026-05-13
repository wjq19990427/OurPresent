from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from tools.synth.actions import build_script
from tools.synth.driver import SynthConfigError, run_script, validate_synth_storage
from tools.synth.persona import load_persona_seed
from tools.synth.script_io import dumps_md, load_md, loads_md
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


def test_markdown_round_trip_preserves_script() -> None:
    script = _script()

    assert loads_md(dumps_md(script)) == script


def test_sessions_are_created_on_their_event_day() -> None:
    script = _script()
    event_dates = {event["id"]: event["date"] for event in script["timeline"]}

    for session in script["sessions"]:
        assert session["created_at"].startswith(event_dates[session["event_id"]])
        assert session["fields"]["content_time"] == event_dates[session["event_id"]]


@pytest.mark.parametrize(
    ("broken_text", "message"),
    [
        (dumps_md(_script()).replace("---\n", "", 1), "frontmatter"),
        (
            dumps_md(_script()).replace("\npersonas:\n", "\nmissing_personas:\n"),
            "script missing required field: personas",
        ),
        (
            dumps_md(_script()).replace("    at: 2026-01-10 10:01:00\n", "", 1),
            "sessions[1].actions[0].at",
        ),
    ],
)
def test_replay_rejects_bad_markdown_before_db_created(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    broken_text: str,
    message: str,
) -> None:
    script_path = tmp_path / "broken.md"
    db_path = tmp_path / "synth" / "data" / "database.db"
    script_path.write_text(broken_text, "utf-8")
    monkeypatch.setenv("SYNTH_DB_PATH", str(db_path))

    result = subprocess.run(
        [sys.executable, "tools/synth/replay.py", str(script_path)],
        cwd=Path(__file__).resolve().parents[3],
        env=None,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert message in result.stderr
    assert not db_path.exists()


def test_template_markdown_replays(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "synth" / "data" / "database.db"
    monkeypatch.setenv("SYNTH_DB_PATH", str(db_path))
    template = Path("tools/synth/scripts/template.md")

    run_script(load_md(template))

    assert db_path.exists()


def test_markdown_session_text_edit_reaches_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "synth" / "data" / "database.db"
    script_path = tmp_path / "edited.md"
    new_description = "一次被手工改写后的共享记录描述"
    original = Path("tools/synth/scripts/任务20_合成数据剧本.md").read_text("utf-8")
    edited = original.replace(
        "description: 一次共享记录被读到后的回复",
        f"description: {new_description}",
        1,
    )
    script_path.write_text(edited, "utf-8")
    monkeypatch.setenv("SYNTH_DB_PATH", str(db_path))

    run_script(load_md(script_path))

    with sqlite3.connect(db_path) as conn:
        descriptions = {
            row[0]
            for row in conn.execute("SELECT description FROM sessions").fetchall()
        }

    assert new_description in descriptions


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
