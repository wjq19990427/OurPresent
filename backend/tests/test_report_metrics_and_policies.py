from __future__ import annotations

from datetime import datetime

import pytest

from backend.application.couples import accept_bind, send_bind_request
from backend.application.reports import (
    compute_footprint,
    compute_suspense,
    partner_enabled_status,
    service_active_for_couple,
)
from backend.domain.models import SessionRecord
from backend.infrastructure.database.sessions_repo import add_session
from backend.infrastructure.database.users_repo import create_user, update_user


def _session(**fields: object) -> SessionRecord:
    defaults = {
        "session_id": "sess_1",
        "user_id": "usr_1",
        "couple_id": "cp_1",
        "status": "final",
        "visibility": "shared",
        "unlock_requested_at": None,
        "unlock_at": None,
        "shared_at": "2026-05-02 10:00:00",
        "upload_time": "2026-05-02 09:00:00",
        "archive_time": "2026-05-02 09:30:00",
        "is_complete": True,
    }
    defaults.update(fields)
    return SessionRecord(**defaults)


def _active_couple() -> tuple[str, str, str]:
    alice = create_user("alice", "secret123")
    bob = create_user("bob", "secret123")
    couple = send_bind_request(alice.user_id, bob.user_id)
    accept_bind(couple.couple_id)
    return alice.user_id, bob.user_id, couple.couple_id


def test_compute_footprint_empty_sessions() -> None:
    footprint = compute_footprint(
        [],
        (datetime(2026, 5, 1), datetime(2026, 5, 7, 23, 59, 59)),
    )

    assert footprint == {
        "total": 0,
        "by_kind": {"photo": 0, "video": 0, "text": 0},
        "active_days": 0,
        "comment_count": 0,
        "by_author": {},
    }


def test_compute_footprint_single_author_counts_comments_and_days() -> None:
    sessions = [
        _session(session_id="sess_1", comments=[{"id": "c1"}, {"id": "c2"}]),
        _session(session_id="sess_2", shared_at="2026-05-03 11:00:00"),
    ]

    footprint = compute_footprint(
        sessions,
        (datetime(2026, 5, 1), datetime(2026, 5, 7, 23, 59, 59)),
    )

    assert footprint["total"] == 2
    assert footprint["active_days"] == 2
    assert footprint["comment_count"] == 2
    assert footprint["by_author"] == {"usr_1": 2}


def test_compute_footprint_rejects_session_without_shared_at() -> None:
    sessions = [_session(shared_at=None)]

    with pytest.raises(ValueError, match="shared_at"):
        compute_footprint(
            sessions,
            (datetime(2026, 5, 1), datetime(2026, 5, 7, 23, 59, 59)),
        )


def test_compute_footprint_two_authors_and_multiple_kinds() -> None:
    sessions = [
        _session(
            session_id="sess_photo",
            user_id="usr_a",
            files=[{"filename": "photo.jpg"}],
            source_type="file",
        ),
        _session(
            session_id="sess_video",
            user_id="usr_b",
            files=[{"filename": "clip.mp4"}],
            source_type="file",
        ),
        _session(session_id="sess_text", user_id="usr_b", source_type="text"),
    ]

    footprint = compute_footprint(
        sessions,
        (datetime(2026, 5, 1), datetime(2026, 5, 7, 23, 59, 59)),
    )

    assert footprint["by_kind"] == {"photo": 1, "video": 1, "text": 1}
    assert footprint["by_author"] == {"usr_a": 1, "usr_b": 2}


def test_compute_suspense_filters_pending_unlock_and_orders_by_unlock_at() -> None:
    now = datetime(2026, 5, 1, 12, 0, 0)
    add_session(
        _session(
            session_id="later",
            visibility="pending_unlock",
            unlock_at="2026-05-05 12:00:00",
            files=[{"filename": "photo.jpg"}],
            source_type="file",
        )
    )
    add_session(
        _session(
            session_id="shared",
            visibility="shared",
            unlock_at="2026-05-02 12:00:00",
        )
    )
    add_session(
        _session(
            session_id="sooner",
            visibility="pending_unlock",
            unlock_at="2026-05-03 11:00:00",
            files=[{"filename": "clip.mp4"}],
            source_type="file",
        )
    )

    suspense = compute_suspense("cp_1", now)

    assert suspense == [
        {
            "session_id": "sooner",
            "unlock_at": "2026-05-03 11:00:00",
            "days_remaining": 2,
            "kind": "video",
        },
        {
            "session_id": "later",
            "unlock_at": "2026-05-05 12:00:00",
            "days_remaining": 4,
            "kind": "photo",
        },
    ]


def test_service_active_for_couple_requires_both_users_enabled() -> None:
    alice_id, bob_id, couple_id = _active_couple()

    assert service_active_for_couple(couple_id) is False
    assert partner_enabled_status(alice_id) == "neither"

    update_user(alice_id, {"weekly_report_enabled": True})
    assert service_active_for_couple(couple_id) is False
    assert partner_enabled_status(alice_id) == "only_self"
    assert partner_enabled_status(bob_id) == "only_partner"

    update_user(bob_id, {"weekly_report_enabled": True})
    assert service_active_for_couple(couple_id) is True
    assert partner_enabled_status(alice_id) == "both"

    update_user(alice_id, {"weekly_report_enabled": False})
    assert service_active_for_couple(couple_id) is False
    assert partner_enabled_status(alice_id) == "only_partner"
