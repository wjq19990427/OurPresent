from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from PIL import Image

from backend.application.maintenance import load_db_with_tick, tick
from backend.domain.models import SessionRecord
from backend.infrastructure.ai.agent_skills import get_report_history, get_shared_sessions_for_rag
from backend.infrastructure.database import db as db_module
from backend.infrastructure.database.sessions_repo import add_session
from backend.infrastructure.database.users_repo import create_user
from backend.infrastructure.media import thumbnails


def test_tick_unlocks_sessions_and_cleans_expired_tokens() -> None:
    old_upload = (datetime.now() - timedelta(days=91)).strftime("%Y-%m-%d %H:%M:%S")
    future = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    past = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    db = {
        "users": [],
        "couples": [],
        "sessions": [
            {
                "session_id": "session_1",
                "user_id": "usr_1",
                "couple_id": "cp_1",
                "visibility": "pending_unlock",
                "upload_time": old_upload,
            }
        ],
        "auth_tokens": [
            {"token": "expired", "user_id": "usr_1", "expires_at": past},
            {"token": "valid", "user_id": "usr_1", "expires_at": future},
        ],
    }

    changed = tick(db)

    assert changed is True
    assert db["sessions"][0]["visibility"] == "shared"
    assert db["sessions"][0]["shared_at"]
    assert [token["token"] for token in db["auth_tokens"]] == ["valid"]


def test_load_db_with_tick_persists_frozen_couple_cleanup(tmp_path) -> None:
    user_a = create_user("alice", "secret123")
    user_b = create_user("bob", "secret123")
    attachment = tmp_path / "Assets" / "Final" / "session_2_000_photo.jpg"
    attachment.write_bytes(b"img")
    (tmp_path / "Assets" / "Final" / "session_2.md").write_text("archived", encoding="utf-8")
    expired = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    db_module.save_db(
        {
            "users": [
                {
                    **user_a.to_dict(),
                    "couple_id": "cp_1",
                },
                {
                    **user_b.to_dict(),
                    "couple_id": "cp_1",
                },
            ],
            "couples": [
                {
                    "couple_id": "cp_1",
                    "user_a": user_a.user_id,
                    "user_b": user_b.user_id,
                    "created_at": "2026-05-01 10:00:00",
                    "couple_status": "frozen",
                    "uncouple_initiated_by": user_a.user_id,
                    "uncouple_initiated_at": "2026-05-01 10:00:00",
                    "both_agreed_uncouple": False,
                    "freeze_ends_at": expired,
                }
            ],
            "sessions": [
                SessionRecord(
                    session_id="session_2",
                    user_id=user_a.user_id,
                    couple_id="cp_1",
                    status="final",
                    visibility="shared",
                    unlock_requested_at=None,
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
                ).to_dict()
            ],
            "auth_tokens": [],
        }
    )

    db = load_db_with_tick()

    assert db["sessions"] == []
    assert db["couples"][0]["couple_status"] == "dissolved"
    assert all(user["couple_id"] is None for user in db["users"])
    assert not attachment.exists()


def test_ai_helpers_filter_shared_sessions_and_raise_for_unimplemented_reports() -> None:
    add_session(
        SessionRecord(
            session_id="session_3",
            user_id="usr_1",
            couple_id="cp_1",
            status="final",
            visibility="shared",
            unlock_requested_at=None,
            shared_at="2026-05-01 12:00:00",
            upload_time="2026-05-01 10:00:00",
            archive_time="2026-05-01 11:00:00",
            is_complete=True,
        )
    )
    add_session(
        SessionRecord(
            session_id="session_4",
            user_id="usr_2",
            couple_id="cp_1",
            status="final",
            visibility="private",
            unlock_requested_at=None,
            shared_at=None,
            upload_time="2026-05-01 10:00:00",
            archive_time="2026-05-01 11:00:00",
            is_complete=True,
        )
    )

    shared = get_shared_sessions_for_rag("cp_1")

    assert [item["session_id"] for item in shared] == ["session_3"]
    with pytest.raises(NotImplementedError, match="周报功能尚未实现"):
        get_report_history("cp_1")


def test_video_thumbnail_unavailable_and_failure_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(thumbnails, "_CV2_AVAILABLE", False)
    assert thumbnails.video_thumbnail("video.mp4") == (None, "⚠ 预览不可用（缺少 cv2/PIL）")

    class FakeCapture:
        def read(self):
            return False, None

        def release(self):
            pass

    class FakeCV2:
        @staticmethod
        def VideoCapture(_path):
            return FakeCapture()

    monkeypatch.setattr(thumbnails, "_CV2_AVAILABLE", True)
    monkeypatch.setattr(thumbnails, "cv2", FakeCV2)
    assert thumbnails.video_thumbnail("video.mp4") == (None, "视频读取失败")


def test_pil_to_png_bytes_returns_png_bytes() -> None:
    img = Image.new("RGB", (4, 4), color="red")

    content = thumbnails.pil_to_png_bytes(img)

    assert content.startswith(b"\x89PNG")
