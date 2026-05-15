from __future__ import annotations

from datetime import datetime

import pytest

from backend.application.maintenance import ticking
from backend.application.maintenance.ticking import tick
from backend.application.reports.scheduling import (
    previous_report_window_end,
    should_generate_for_couple,
)
from backend.domain.models import Couple, Report

NOW = datetime(2026, 5, 11, 10, 0, 0)


class FrozenDateTime(datetime):
    @classmethod
    def now(cls) -> datetime:
        return NOW


@pytest.fixture(autouse=True)
def reset_tick_state(monkeypatch: pytest.MonkeyPatch) -> None:
    ticking._failed_retry_consumed_report_ids.clear()
    monkeypatch.setattr(ticking, "datetime", FrozenDateTime)


def _couple(
    couple_id: str = "cp_1",
    *,
    user_a: str = "usr_a",
    user_b: str = "usr_b",
    status: str = "active",
    interval_days: int = 7,
    created_at: str = "2026-05-01 10:00:00",
) -> Couple:
    return Couple(
        couple_id=couple_id,
        user_a=user_a,
        user_b=user_b,
        created_at=created_at,
        couple_status=status,
        uncouple_initiated_by=None,
        uncouple_initiated_at=None,
        both_agreed_uncouple=False,
        freeze_ends_at=None,
        cancel_uncouple_requested_by=None,
        cancel_uncouple_requested_at=None,
        weekly_report_interval_days=interval_days,
    )


def _raw_couple(couple: Couple) -> dict:
    return couple.to_dict()


def _user(user_id: str, *, enabled: bool) -> dict:
    return {
        "user_id": user_id,
        "username": user_id,
        "password_hash": "hash",
        "couple_id": "cp_1",
        "joined_at": "2026-05-01 09:00:00",
        "weekly_report_enabled": enabled,
    }


def _report(
    couple_id: str = "cp_1",
    *,
    report_id: str = "rpt_20260501_cp_1",
    status: str = "ready",
    window_end: str = "2026-05-01 10:00:00",
    generated_at: str = "2026-05-01 10:01:00",
) -> dict:
    return {
        "report_id": report_id,
        "couple_id": couple_id,
        "window_start": "2026-04-24 10:00:00",
        "window_end": window_end,
        "generated_at": generated_at,
        "model_version": "",
        "footprint": {},
        "weather": {},
        "resonance": [],
        "suspense": [],
        "status": status,
        "source_session_ids": [],
    }


def _db(
    couple: Couple,
    *,
    user_a_enabled: bool = True,
    user_b_enabled: bool = True,
    reports: list[dict] | None = None,
    retry_consumed: set[str] | None = None,
) -> dict:
    return {
        "users": [
            {**_user(couple.user_a, enabled=user_a_enabled), "couple_id": couple.couple_id},
            {**_user(couple.user_b, enabled=user_b_enabled), "couple_id": couple.couple_id},
        ],
        "couples": [_raw_couple(couple)],
        "sessions": [],
        "auth_tokens": [],
        "reports": list(reports or []),
        "_weekly_report_retry_consumed": set(retry_consumed or set()),
    }


@pytest.mark.parametrize(
    ("couple", "db_kwargs", "expected"),
    [
        (_couple(status="frozen"), {}, False),
        (_couple(status="dissolved"), {}, False),
        (_couple(status="pending_bind"), {}, False),
        (_couple(), {"user_a_enabled": False, "user_b_enabled": False}, False),
        (_couple(), {"user_a_enabled": True, "user_b_enabled": False}, False),
        (_couple(created_at="2026-05-10 10:00:00"), {}, False),
        (_couple(created_at="2026-05-01 10:00:00"), {}, True),
        (_couple(), {"reports": [_report(window_end="2026-05-10 10:00:00")]}, False),
        (_couple(), {"reports": [_report(window_end="2026-05-01 10:00:00")]}, True),
        (
            _couple(),
            {
                "reports": [
                    _report(
                        report_id="failed_1",
                        status="failed",
                        window_end="2026-05-10 10:00:00",
                    )
                ]
            },
            True,
        ),
        (
            _couple(),
            {
                "reports": [
                    _report(report_id="failed_1", status="failed", window_end="2026-05-10 10:00:00")
                ],
                "retry_consumed": {"failed_1"},
            },
            False,
        ),
    ],
)
def test_should_generate_for_couple_state_combinations(
    couple: Couple,
    db_kwargs: dict,
    expected: bool,
) -> None:
    assert should_generate_for_couple(couple, _db(couple, **db_kwargs), NOW) is expected


def test_previous_report_window_end_returns_latest_window_end() -> None:
    couple = _couple()
    db = _db(
        couple,
        reports=[
            _report(report_id="older", window_end="2026-05-01 10:00:00"),
            _report(report_id="newer", window_end="2026-05-08 10:00:00"),
        ],
    )

    assert previous_report_window_end(couple.couple_id, db) == datetime(2026, 5, 8, 10, 0, 0)


def _generated_report(couple_id: str, *, status: str = "ready") -> Report:
    return Report(
        report_id=f"rpt_20260511_{couple_id}",
        couple_id=couple_id,
        window_start="2026-05-04 10:00:00",
        window_end="2026-05-11 10:00:00",
        generated_at="2026-05-11 10:00:01",
        model_version="test",
        status=status,
    )


def test_tick_report_failure_for_one_couple_does_not_block_others(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    couple_a = _couple("cp_a", user_a="usr_a1", user_b="usr_a2")
    couple_b = _couple("cp_b", user_a="usr_b1", user_b="usr_b2")
    db = {
        "users": [
            {**_user("usr_a1", enabled=True), "couple_id": "cp_a"},
            {**_user("usr_a2", enabled=True), "couple_id": "cp_a"},
            {**_user("usr_b1", enabled=True), "couple_id": "cp_b"},
            {**_user("usr_b2", enabled=True), "couple_id": "cp_b"},
        ],
        "couples": [_raw_couple(couple_a), _raw_couple(couple_b)],
        "sessions": [],
        "auth_tokens": [],
        "reports": [
            _report("cp_a", report_id="old_a", window_end="2026-05-01 10:00:00"),
            _report("cp_b", report_id="old_b", window_end="2026-05-01 10:00:00"),
        ],
    }

    def fake_generate(couple_id: str, _now: datetime) -> Report:
        if couple_id == "cp_a":
            raise RuntimeError("boom")
        return _generated_report(couple_id)

    monkeypatch.setattr(ticking, "generate_weekly_report", fake_generate)

    assert tick(db) is True
    assert any(report["report_id"] == "rpt_20260511_cp_b" for report in db["reports"])
    assert not any(report["report_id"] == "rpt_20260511_cp_a" for report in db["reports"])


def test_tick_failed_retry_then_failed_is_skipped_until_next_period(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    couple = _couple(interval_days=7)
    db = _db(
        couple,
        reports=[_report(report_id="old_ready", status="ready", window_end="2026-05-01 10:00:00")],
    )
    calls: list[str] = []

    def fake_generate(couple_id: str, _now: datetime) -> Report:
        calls.append(couple_id)
        return _generated_report(couple_id, status="failed")

    monkeypatch.setattr(ticking, "generate_weekly_report", fake_generate)

    assert tick(db) is True
    assert tick(db) is True
    assert tick(db) is False
    assert calls == [couple.couple_id, couple.couple_id]
