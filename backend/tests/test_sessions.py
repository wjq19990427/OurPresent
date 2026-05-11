from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from backend.application.sessions.comments import add_comment, delete_comment
from backend.application.sessions.creation import save_session_final, save_session_pending
from backend.application.sessions.editing import (
    append_to_session,
    move_to_final,
    update_session_fields,
)
from backend.application.sessions.export import collect_export_files
from backend.application.sessions.sharing import (
    can_view_session,
    request_unlock,
    reschedule_unlock,
    revoke_unlock,
    unlock_now,
)
from backend.application.sessions.validation import is_text_session, validate_session
from backend.domain.models import SessionRecord
from backend.infrastructure.database.sessions_repo import (
    add_session,
    get_session_by_id,
    list_sessions_for_user,
    replace_session,
)
from backend.infrastructure.database.users_repo import create_user, update_user
from frontend.streamlit_app.components import _unlock_at_for_choice


def _session_record(**fields: object) -> SessionRecord:
    defaults = {
        "session_id": "session_test",
        "user_id": "usr_1",
        "couple_id": None,
        "status": "pending",
        "visibility": "private",
        "unlock_requested_at": None,
        "unlock_at": None,
        "shared_at": None,
        "upload_time": "2026-05-01 10:00:00",
        "archive_time": "",
        "is_complete": False,
    }
    defaults.update(fields)
    return SessionRecord(**defaults)


def test_validation_helpers_detect_text_sessions_and_required_fields() -> None:
    assert is_text_session(_session_record(source_type="text", files=[])) is True
    assert is_text_session(_session_record(files=[{"filename": "memo.txt"}])) is True
    assert is_text_session(_session_record(files=[{"filename": "photo.jpg"}])) is False

    missing = validate_session(
        _session_record(source_type="file", content_time="", description="", feeling="")
    )
    assert missing == ["创建时间", "描述", "感受"]

    text_missing = validate_session(
        _session_record(source_type="text", content_time="", description="", feeling="")
    )
    assert text_missing == ["创建时间", "感受"]


def test_save_session_pending_writes_files_and_marks_incomplete() -> None:
    user = create_user("alice", "secret123")

    save_session_pending(
        user.user_id,
        None,
        [(b"hello", "note.txt")],
        "text",
        {"content_time": "", "description": "", "feeling": ""},
    )

    stored = list_sessions_for_user(user.user_id)
    assert len(stored) == 1
    assert stored[0].status == "pending"
    assert stored[0].is_complete is False
    sessions = collect_export_files(user.user_id)
    assert len(sessions) == 1
    assert sessions[0].read_bytes() == b"hello"


def test_save_session_final_writes_markdown_and_complete() -> None:
    user = create_user("alice", "secret123")

    save_session_final(
        user.user_id,
        None,
        [(b"photo", "photo.jpg")],
        "file",
        {
            "content_time": "2026-05-01",
            "description": "海边散步",
            "feeling": "开心",
            "reason": "纪念",
        },
    )

    stored = list_sessions_for_user(user.user_id)
    assert len(stored) == 1
    assert stored[0].status == "final"
    assert stored[0].is_complete is True
    exported = collect_export_files(user.user_id)
    assert len(exported) == 1
    md_path = exported[0].parent / (exported[0].stem.split("_000_")[0] + ".md")
    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")
    assert "海边散步" in content
    assert "开心" in content


def test_move_to_final_moves_pending_files_and_writes_markdown() -> None:
    attachment = Path("Assets/Pending/session_1_000_note.txt")
    attachment.parent.mkdir(parents=True, exist_ok=True)
    attachment.write_bytes(b"draft")
    session = SessionRecord(
        session_id="session_1",
        user_id="usr_1",
        couple_id=None,
        status="pending",
        visibility="private",
        unlock_requested_at=None,
        unlock_at=None,
        shared_at=None,
        upload_time="2026-05-01 10:00:00",
        archive_time="",
        is_complete=False,
        files=[{"filename": attachment.name, "original_name": "note.txt", "path": str(attachment)}],
        source_type="text",
        content_time="2026-05-01",
        feeling="平静",
    )
    add_session(session)

    move_to_final("session_1")

    updated = get_session_by_id("session_1")
    assert updated is not None
    assert updated.status == "final"
    final_path = Path(updated.files[0]["path"])
    assert final_path.exists()
    assert not attachment.exists()
    assert (final_path.parent / "session_1.md").exists()


def test_update_session_fields_records_history_for_final_non_text() -> None:
    session = SessionRecord(
        session_id="session_2",
        user_id="usr_1",
        couple_id=None,
        status="final",
        visibility="private",
        unlock_requested_at=None,
        unlock_at=None,
        shared_at=None,
        upload_time="2026-05-01 10:00:00",
        archive_time="2026-05-01 11:00:00",
        is_complete=True,
        source_type="file",
        content_time="2026-05-01",
        description="旧描述",
        feeling="旧感受",
    )
    add_session(session)

    update_session_fields("session_2", {"description": "新描述", "feeling": "新感受"})

    updated = get_session_by_id("session_2")
    assert updated is not None
    assert updated.description == "新描述"
    assert updated.feeling == "新感受"
    assert len(updated.edit_history) == 1
    assert updated.edit_history[0]["changes"]["description"]["from"] == "旧描述"


def test_update_session_fields_skips_text_description_history() -> None:
    session = SessionRecord(
        session_id="session_3",
        user_id="usr_1",
        couple_id=None,
        status="final",
        visibility="private",
        unlock_requested_at=None,
        unlock_at=None,
        shared_at=None,
        upload_time="2026-05-01 10:00:00",
        archive_time="2026-05-01 11:00:00",
        is_complete=True,
        source_type="text",
        content_time="2026-05-01",
        description="旧描述",
        feeling="旧感受",
    )
    add_session(session)

    update_session_fields("session_3", {"description": "新描述"})

    updated = get_session_by_id("session_3")
    assert updated is not None
    assert updated.description == "新描述"
    assert updated.edit_history == []


def test_comments_add_and_delete_rewrite_markdown(tmp_path: Path) -> None:
    md_dir = tmp_path / "Assets" / "Final"
    md_dir.mkdir(parents=True, exist_ok=True)
    session = SessionRecord(
        session_id="session_4",
        user_id="usr_1",
        couple_id=None,
        status="final",
        visibility="private",
        unlock_requested_at=None,
        unlock_at=None,
        shared_at=None,
        upload_time="2026-05-01 10:00:00",
        archive_time="2026-05-01 11:00:00",
        is_complete=True,
        source_type="file",
        content_time="2026-05-01",
        description="desc",
        feeling="feel",
    )
    add_session(session)

    add_comment("session_4", "usr_2", "第一条评论")
    stored = get_session_by_id("session_4")
    assert stored is not None
    assert len(stored.comments) == 1
    comment_id = stored.comments[0]["id"]

    delete_comment("session_4", comment_id)
    stored = get_session_by_id("session_4")
    assert stored is not None
    assert stored.comments == []
    assert "评论区" not in (md_dir / "session_4.md").read_text(encoding="utf-8")


def test_sharing_and_view_permissions() -> None:
    owner = create_user("alice", "secret123")
    partner = create_user("bob", "secret123")
    outsider = create_user("carol", "secret123")
    update_user(owner.user_id, {"couple_id": "cp_1"})
    update_user(partner.user_id, {"couple_id": "cp_1"})
    session = SessionRecord(
        session_id="session_5",
        user_id=owner.user_id,
        couple_id="cp_1",
        status="final",
        visibility="private",
        unlock_requested_at=None,
        unlock_at=None,
        shared_at=None,
        upload_time="2026-05-01 10:00:00",
        archive_time="2026-05-01 11:00:00",
        is_complete=True,
    )
    add_session(session)

    stored = get_session_by_id("session_5")
    assert stored is not None
    assert can_view_session(stored, owner.user_id) is True
    assert can_view_session(stored, partner.user_id) is False
    assert can_view_session(stored, outsider.user_id) is False

    unlock_at = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    request_unlock("session_5", unlock_at)
    stored = get_session_by_id("session_5")
    assert stored is not None
    assert stored.visibility == "pending_unlock"
    assert stored.unlock_requested_at
    assert stored.unlock_at == unlock_at

    revoke_unlock("session_5")
    stored = get_session_by_id("session_5")
    assert stored is not None
    assert stored.visibility == "private"
    assert stored.unlock_requested_at is None
    assert stored.unlock_at is None

    stored.visibility = "shared"
    replace_session(stored)
    assert can_view_session(stored, partner.user_id) is True


def test_request_unlock_immediate_shares_without_pending_snapshot() -> None:
    session = _session_record(session_id="session_now", status="final")
    add_session(session)
    past = (datetime.now() - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")

    request_unlock("session_now", past)

    stored = get_session_by_id("session_now")
    assert stored is not None
    assert stored.visibility == "shared"
    assert stored.unlock_requested_at
    assert stored.shared_at
    assert stored.unlock_at == stored.shared_at


def test_append_to_pending_unlock_session_preserves_original_without_history() -> None:
    session = _session_record(
        session_id="session_append",
        status="final",
        visibility="pending_unlock",
        unlock_requested_at="2026-05-01 10:00:00",
        unlock_at="2026-05-18 10:00:00",
        feeling="原来的感受",
        edit_history=[],
    )
    add_session(session)

    append_to_session("session_append", "feeling", "后来又想补充一句")

    stored = get_session_by_id("session_append")
    assert stored is not None
    assert stored.feeling.startswith("原来的感受")
    assert "[追加于 " in stored.feeling
    assert "后来又想补充一句" in stored.feeling
    assert stored.edit_history == []


def test_unlock_now_sets_shared_state_and_aligns_times() -> None:
    session = _session_record(
        session_id="session_unlock_now",
        visibility="pending_unlock",
        unlock_requested_at="2026-05-01 10:00:00",
        unlock_at=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
    )
    add_session(session)

    unlock_now("session_unlock_now")

    stored = get_session_by_id("session_unlock_now")
    assert stored is not None
    assert stored.visibility == "shared"
    assert stored.shared_at
    assert stored.unlock_at == stored.shared_at
    assert stored.unlock_requested_at == "2026-05-01 10:00:00"


def test_reschedule_unlock_future_keeps_pending_and_request_time() -> None:
    session = _session_record(
        session_id="session_reschedule",
        visibility="pending_unlock",
        unlock_requested_at="2026-05-01 10:00:00",
        unlock_at=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
    )
    add_session(session)
    new_unlock_at = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

    reschedule_unlock("session_reschedule", new_unlock_at)

    stored = get_session_by_id("session_reschedule")
    assert stored is not None
    assert stored.visibility == "pending_unlock"
    assert stored.unlock_at == new_unlock_at
    assert stored.unlock_requested_at == "2026-05-01 10:00:00"


def test_reschedule_unlock_past_unlocks_immediately() -> None:
    session = _session_record(
        session_id="session_reschedule_past",
        visibility="pending_unlock",
        unlock_requested_at="2026-05-01 10:00:00",
        unlock_at=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
    )
    add_session(session)
    past_unlock_at = (datetime.now() - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")

    reschedule_unlock("session_reschedule_past", past_unlock_at)

    stored = get_session_by_id("session_reschedule_past")
    assert stored is not None
    assert stored.visibility == "shared"
    assert stored.shared_at
    assert stored.unlock_at == stored.shared_at


def test_pending_unlock_actions_reject_non_pending_visibility() -> None:
    private_session = _session_record(session_id="session_private", visibility="private")
    shared_session = _session_record(session_id="session_shared", visibility="shared")
    add_session(private_session)
    add_session(shared_session)

    with pytest.raises(ValueError, match="pending_unlock"):
        append_to_session("session_private", "feeling", "补充")
    with pytest.raises(ValueError, match="pending_unlock"):
        unlock_now("session_private")
    with pytest.raises(ValueError, match="pending_unlock"):
        reschedule_unlock("session_shared", "2026-05-12 10:00:00")


def test_append_to_session_rejects_non_text_field() -> None:
    session = _session_record(
        session_id="session_append_invalid",
        visibility="pending_unlock",
        unlock_requested_at="2026-05-01 10:00:00",
        unlock_at="2026-05-18 10:00:00",
    )
    add_session(session)

    with pytest.raises(ValueError, match="appendable"):
        append_to_session("session_append_invalid", "content_time", "2026-05-02")


def test_unlock_choice_defaults_and_custom_dates() -> None:
    anchor = datetime(2026, 5, 11, 9, 30, 0)

    assert _unlock_at_for_choice("1 周后", anchor=anchor) == "2026-05-18 09:30:00"
    assert _unlock_at_for_choice("立即", anchor=anchor) == "2026-05-11 09:30:00"
    assert (
        _unlock_at_for_choice("自定义日期", date(2026, 5, 20), anchor)
        == "2026-05-20 09:30:00"
    )
    assert (
        _unlock_at_for_choice("自定义日期", date(2026, 5, 11), anchor)
        == "2026-05-11 09:30:00"
    )


def test_collect_export_files_returns_only_existing_paths(tmp_path: Path) -> None:
    existing = tmp_path / "Assets" / "Final" / "kept.txt"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("hello", encoding="utf-8")
    session = SessionRecord(
        session_id="session_6",
        user_id="usr_1",
        couple_id=None,
        status="final",
        visibility="private",
        unlock_requested_at=None,
        unlock_at=None,
        shared_at=None,
        upload_time="2026-05-01 10:00:00",
        archive_time="2026-05-01 11:00:00",
        is_complete=True,
        files=[
            {"filename": existing.name, "original_name": "kept.txt", "path": str(existing)},
            {
                "filename": "missing.txt",
                "original_name": "missing.txt",
                "path": str(existing.parent / "missing.txt"),
            },
        ],
    )
    add_session(session)

    exported = collect_export_files("usr_1")

    assert exported == [existing]
