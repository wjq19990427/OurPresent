from __future__ import annotations

from pathlib import Path

import pytest

from backend.application.couples import (
    CoupleError,
    accept_bind,
    confirm_uncouple,
    is_frozen,
    reject_bind,
    send_bind_request,
    start_uncouple,
)
from backend.domain.models import SessionRecord
from backend.infrastructure.database.couples_repo import (
    get_couple_by_id,
    get_couple_for_user,
    get_pending_requests_for_user,
    update_couple,
)
from backend.infrastructure.database.sessions_repo import add_session
from backend.infrastructure.database.users_repo import create_user, get_user_by_id


def _active_couple() -> tuple[str, str, str]:
    alice = create_user("alice", "secret123")
    bob = create_user("bob", "secret123")
    couple = send_bind_request(alice.user_id, bob.user_id)
    accept_bind(couple.couple_id)
    return alice.user_id, bob.user_id, couple.couple_id


def test_bind_request_accept_and_pending_lookup() -> None:
    alice = create_user("alice", "secret123")
    bob = create_user("bob", "secret123")

    couple = send_bind_request(alice.user_id, bob.user_id)
    pending = get_pending_requests_for_user(bob.user_id)

    assert couple.couple_status == "pending_bind"
    assert [item.couple_id for item in pending] == [couple.couple_id]

    accept_bind(couple.couple_id)

    accepted = get_couple_by_id(couple.couple_id)
    assert accepted is not None
    assert accepted.couple_status == "active"
    assert get_user_by_id(alice.user_id).couple_id == couple.couple_id
    assert get_user_by_id(bob.user_id).couple_id == couple.couple_id


def test_reject_bind_removes_pending_request() -> None:
    alice = create_user("alice", "secret123")
    bob = create_user("bob", "secret123")
    couple = send_bind_request(alice.user_id, bob.user_id)

    reject_bind(couple.couple_id)

    assert get_couple_by_id(couple.couple_id) is None
    assert get_pending_requests_for_user(bob.user_id) == []


def test_send_bind_request_policy_errors() -> None:
    alice = create_user("alice", "secret123")
    bob = create_user("bob", "secret123")
    carol = create_user("carol", "secret123")

    with pytest.raises(CoupleError, match="不能向自己发送绑定请求"):
        send_bind_request(alice.user_id, alice.user_id)

    with pytest.raises(CoupleError, match="找不到 ID"):
        send_bind_request(alice.user_id, "missing")

    active = send_bind_request(alice.user_id, bob.user_id)
    accept_bind(active.couple_id)
    with pytest.raises(CoupleError, match="已有绑定关系"):
        send_bind_request(carol.user_id, bob.user_id)

    david = create_user("david", "secret123")
    eve = create_user("eve", "secret123")
    frozen = send_bind_request(david.user_id, eve.user_id)
    accept_bind(frozen.couple_id)
    update_couple(frozen.couple_id, {"couple_status": "frozen"})
    with pytest.raises(CoupleError, match="处于冻结期"):
        send_bind_request(carol.user_id, eve.user_id)

    frank = create_user("frank", "secret123")
    grace = create_user("grace", "secret123")
    send_bind_request(frank.user_id, grace.user_id)
    with pytest.raises(CoupleError, match="待确认的绑定请求"):
        send_bind_request(carol.user_id, grace.user_id)


def test_start_uncouple_marks_couple_frozen() -> None:
    alice_id, _, couple_id = _active_couple()

    start_uncouple(alice_id)

    couple = get_couple_by_id(couple_id)
    assert couple is not None
    assert couple.couple_status == "frozen"
    assert couple.uncouple_initiated_by == alice_id
    assert couple.freeze_ends_at
    assert is_frozen(alice_id) is True


def test_confirm_uncouple_destroys_sessions_and_clears_users(tmp_path: Path) -> None:
    alice_id, bob_id, couple_id = _active_couple()
    start_uncouple(alice_id)
    attachment = tmp_path / "Assets" / "Final" / "sess_1_000_photo.jpg"
    attachment.write_bytes(b"img")
    markdown = tmp_path / "Assets" / "Final" / "sess_1.md"
    markdown.write_text("archived", encoding="utf-8")
    add_session(
        SessionRecord(
            session_id="sess_1",
            user_id=alice_id,
            couple_id=couple_id,
            status="final",
            visibility="shared",
            unlock_requested_at=None,
            unlock_at=None,
            shared_at="2026-05-01 12:00:00",
            upload_time="2026-05-01 10:00:00",
            archive_time="2026-05-01 11:00:00",
            is_complete=True,
            files=[
                {
                    "filename": attachment.name,
                    "original_name": "photo.jpg",
                    "path": str(attachment),
                }
            ],
        )
    )

    confirm_uncouple(bob_id)

    assert get_couple_for_user(alice_id) is None
    dissolved = get_couple_by_id(couple_id)
    assert dissolved is not None
    assert dissolved.couple_status == "dissolved"
    assert get_user_by_id(alice_id).couple_id is None
    assert get_user_by_id(bob_id).couple_id is None
    assert not attachment.exists()
    assert not markdown.exists()
