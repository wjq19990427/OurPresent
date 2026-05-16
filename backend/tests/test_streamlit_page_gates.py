from __future__ import annotations

from datetime import datetime, timedelta

from backend.domain.models import Couple, SessionRecord
from frontend.streamlit_app.pages.tab_mine import (
    _can_create_records,
    _next_unlock_label,
    _recording_gate_message,
    _should_show_first_record_guide,
)
from frontend.streamlit_app.pages.tab_settings import _weekly_report_toggle_available
from frontend.streamlit_app.pages.tab_us import _should_show_first_shared_moment


def _couple(status: str) -> Couple:
    return Couple(
        couple_id="cp_1",
        user_a="usr_a",
        user_b="usr_b",
        created_at="2026-05-01 10:00:00",
        couple_status=status,
        uncouple_initiated_by=None,
        uncouple_initiated_at=None,
        both_agreed_uncouple=False,
        freeze_ends_at=None,
    )


def _session(
    *,
    visibility: str,
    unlock_at: str | None = None,
    shared_at: str | None = None,
) -> SessionRecord:
    return SessionRecord(
        session_id="sess_1",
        user_id="usr_a",
        couple_id="cp_1",
        status="final",
        visibility=visibility,
        unlock_requested_at=None,
        unlock_at=unlock_at,
        shared_at=shared_at,
        upload_time="2026-05-01 10:00:00",
        archive_time="2026-05-01 10:00:00",
        is_complete=True,
    )


def test_mine_tab_requires_active_couple_for_recording() -> None:
    assert _can_create_records(None) is False
    assert _can_create_records(_couple("pending_bind")) is False
    assert _can_create_records(_couple("frozen")) is False
    assert _can_create_records(_couple("active")) is True


def test_mine_tab_gate_message_matches_unbound_state() -> None:
    assert _recording_gate_message(None) == (
        "先去「设置」里绑定伴侣。关系连上后，这里就会开始留下只属于你的记录。"
    )
    assert (
        _recording_gate_message(_couple("pending_bind")) == "等绑定确认后，这里会打开写记录和共享。"
    )
    assert _recording_gate_message(_couple("active")) is None


def test_weekly_report_toggle_only_available_after_binding() -> None:
    assert _weekly_report_toggle_available(None) is False
    assert _weekly_report_toggle_available(_couple("pending_bind")) is False
    assert _weekly_report_toggle_available(_couple("frozen")) is False
    assert _weekly_report_toggle_available(_couple("active")) is True


def test_mine_tab_first_record_guide_only_shows_for_active_empty_couple() -> None:
    assert _should_show_first_record_guide(None, []) is False
    assert _should_show_first_record_guide(_couple("pending_bind"), []) is False
    assert (
        _should_show_first_record_guide(_couple("active"), [_session(visibility="private")])
        is False
    )
    assert _should_show_first_record_guide(_couple("active"), []) is True


def test_waiting_group_unlock_summary_prefers_nearest_unlock() -> None:
    soon = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    later = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")

    assert _next_unlock_label([]) is None
    assert (
        _next_unlock_label([_session(visibility="pending_unlock", unlock_at=None)])
        == "最快开放时间待定"
    )
    assert (
        _next_unlock_label([_session(visibility="pending_unlock", unlock_at=soon)])
        == "最快 2 天后开放"
    )
    assert (
        _next_unlock_label([_session(visibility="pending_unlock", unlock_at=later)])
        == "最快 5 天后开放"
    )


def test_first_shared_moment_only_shows_while_first_shared_record_is_recent() -> None:
    recent = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    old = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")

    assert _should_show_first_shared_moment([]) is False
    assert _should_show_first_shared_moment([_session(visibility="private")]) is False
    assert (
        _should_show_first_shared_moment([_session(visibility="shared", shared_at=recent)])
        is True
    )
    assert _should_show_first_shared_moment([_session(visibility="shared", shared_at=old)]) is False
