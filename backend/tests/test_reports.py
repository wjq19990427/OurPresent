from __future__ import annotations

from backend.application.couples import (
    accept_bind,
    confirm_uncouple,
    send_bind_request,
    start_uncouple,
)
from backend.domain.models import Report
from backend.infrastructure.database.reports_repo import (
    create_report,
    delete_reports_for_couple,
    get_report,
    list_reports_for_couple,
    update_report,
)
from backend.infrastructure.database.users_repo import create_user


def _report(report_id: str, couple_id: str, generated_at: str) -> Report:
    return Report(
        report_id=report_id,
        couple_id=couple_id,
        window_start="2026-05-04 00:00:00",
        window_end="2026-05-10 23:59:59",
        generated_at=generated_at,
        model_version="",
        footprint={"total": 3, "by_author": {"usr_1": 2}},
        weather={"tags": [], "narrative": "平稳"},
        resonance=[{"day": "2026-05-06", "topic": "火锅"}],
        suspense=[{"session_id": "sess_1", "days_remaining": 2}],
        status="ready",
        source_session_ids=["sess_1", "sess_2"],
    )


def test_report_repo_create_get_update_and_delete() -> None:
    report = _report("rpt_20260510_cp_1", "cp_1", "2026-05-11 03:00:00")

    create_report(report)

    assert get_report(report.report_id) == report

    report.status = "sparse"
    report.footprint["total"] = 1
    update_report(report)
    assert get_report(report.report_id) == report

    assert delete_reports_for_couple("cp_1") == 1
    assert get_report(report.report_id) is None


def test_list_reports_for_couple_orders_by_generated_at_desc() -> None:
    older = _report("rpt_20260503_cp_1", "cp_1", "2026-05-04 03:00:00")
    newer = _report("rpt_20260510_cp_1", "cp_1", "2026-05-11 03:00:00")
    other = _report("rpt_20260510_cp_2", "cp_2", "2026-05-12 03:00:00")
    create_report(older)
    create_report(newer)
    create_report(other)

    reports = list_reports_for_couple("cp_1")

    assert [report.report_id for report in reports] == [newer.report_id, older.report_id]


def test_confirm_uncouple_deletes_reports_for_couple() -> None:
    alice = create_user("alice", "secret123")
    bob = create_user("bob", "secret123")
    couple = send_bind_request(alice.user_id, bob.user_id)
    accept_bind(couple.couple_id)
    create_report(
        _report("rpt_20260510_" + couple.couple_id, couple.couple_id, "2026-05-11 03:00:00")
    )

    start_uncouple(alice.user_id)
    confirm_uncouple(bob.user_id)

    assert list_reports_for_couple(couple.couple_id) == []
