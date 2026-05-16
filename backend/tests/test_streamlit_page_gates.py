from __future__ import annotations

from backend.domain.models import Couple
from frontend.streamlit_app.pages.tab_mine import _can_create_records, _recording_gate_message
from frontend.streamlit_app.pages.tab_settings import _weekly_report_toggle_available


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


def test_mine_tab_requires_active_couple_for_recording() -> None:
    assert _can_create_records(None) is False
    assert _can_create_records(_couple("pending_bind")) is False
    assert _can_create_records(_couple("frozen")) is False
    assert _can_create_records(_couple("active")) is True


def test_mine_tab_gate_message_matches_unbound_state() -> None:
    assert _recording_gate_message(None) == "先去「设置」里绑定伴侣，这里才会打开写记录和共享。"
    assert (
        _recording_gate_message(_couple("pending_bind")) == "等绑定确认后，这里会打开写记录和共享。"
    )
    assert _recording_gate_message(_couple("active")) is None


def test_weekly_report_toggle_only_available_after_binding() -> None:
    assert _weekly_report_toggle_available(None) is False
    assert _weekly_report_toggle_available(_couple("pending_bind")) is False
    assert _weekly_report_toggle_available(_couple("frozen")) is False
    assert _weekly_report_toggle_available(_couple("active")) is True
