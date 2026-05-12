from __future__ import annotations

from datetime import datetime

import pytest

from backend.application.couples import accept_bind, send_bind_request
from backend.application.reports import check_no_verbatim_quote, generate_weekly_report
from backend.application.reports import generate as generate_module
from backend.application.reports import semantic as semantic_module
from backend.domain.models import Couple, SessionRecord
from backend.infrastructure.ai.llm_client import EmotionTag, LLMClientError, ResonanceItem
from backend.infrastructure.database import users_repo
from backend.infrastructure.database.reports_repo import list_reports_for_couple
from backend.infrastructure.database.sessions_repo import add_session
from backend.infrastructure.database.users_repo import create_user, update_user


def _active_enabled_couple() -> tuple[str, str, str]:
    alice = create_user("alice", "secret123")
    bob = create_user("bob", "secret123")
    couple = send_bind_request(alice.user_id, bob.user_id)
    accept_bind(couple.couple_id)
    update_user(alice.user_id, {"weekly_report_enabled": True})
    update_user(bob.user_id, {"weekly_report_enabled": True})
    return alice.user_id, bob.user_id, couple.couple_id


class _FakeUUID:
    def __init__(self, value: str) -> None:
        self.hex = value


def _session(**fields: object) -> SessionRecord:
    defaults = {
        "session_id": "sess_1",
        "user_id": "usr_1",
        "couple_id": "cp_1",
        "status": "final",
        "visibility": "shared",
        "unlock_requested_at": None,
        "unlock_at": None,
        "shared_at": "2026-05-08 10:00:00",
        "upload_time": "2026-05-08 09:00:00",
        "archive_time": "2026-05-08 09:30:00",
        "is_complete": True,
        "content_time": "2026-05-08",
        "description": "一起散步",
        "feeling": "轻松",
    }
    defaults.update(fields)
    return SessionRecord(**defaults)


def test_guard_allows_short_overlap_and_rejects_long_verbatim_quote() -> None:
    sessions = [_session(description="今天一起做了一顿很香的晚饭", feeling="开心安定")]

    assert (
        check_no_verbatim_quote(
            {"weather": {"narrative": "晚饭之后很安定"}, "resonance": []},
            sessions,
        )
        is True
    )
    assert (
        check_no_verbatim_quote(
            {"weather": {"narrative": "今天一起做了一顿很香的晚饭"}, "resonance": []},
            sessions,
        )
        is False
    )


def test_guard_rejects_generated_visible_text_with_blocked_user_id() -> None:
    sessions = [_session(user_id="usr_a1b2c3d4")]

    assert (
        check_no_verbatim_quote(
            {
                "weather": {
                    "tags": [{"label": "轻松", "weight": 0.7, "phase": "late"}],
                    "narrative": "这周的节奏更柔和",
                },
                "resonance": [{"topic": "散步", "user_a_excerpt": "微风"}],
            },
            sessions,
            blocked_user_ids=["usr_a1b2c3d4"],
        )
        is True
    )
    assert (
        check_no_verbatim_quote(
            {
                "weather": {
                    "tags": [{"label": "轻松", "weight": 0.7, "phase": "late"}],
                    "narrative": "usr_a1b2c3d4 这周的节奏更柔和",
                },
                "resonance": [],
            },
            sessions,
            blocked_user_ids=["usr_a1b2c3d4"],
        )
        is False
    )
    assert (
        check_no_verbatim_quote(
            {
                "weather": {"narrative": "这周的节奏更柔和"},
                "resonance": [{"topic": "usr_a1b2c3d4 的散步"}],
            },
            sessions,
            blocked_user_ids=["usr_a1b2c3d4"],
        )
        is False
    )


def test_generate_weekly_report_sparse_skips_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    alice_id, _, couple_id = _active_enabled_couple()
    add_session(_session(session_id="sess_1", user_id=alice_id, couple_id=couple_id))
    monkeypatch.setattr(
        generate_module,
        "extract_semantic",
        lambda _sessions, _couple: pytest.fail("sparse reports must not call LLM"),
    )

    report = generate_weekly_report(couple_id, datetime(2026, 5, 11, 0, 0, 0))

    assert report.status == "sparse"
    assert report.footprint["total"] == 1
    assert report.weather == {}
    assert report.resonance == []
    assert report.source_session_ids == ["sess_1"]


def test_generate_weekly_report_ready_with_mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    alice_id, bob_id, couple_id = _active_enabled_couple()
    for index, user_id in enumerate([alice_id, bob_id, alice_id], start=1):
        add_session(
            _session(
                session_id=f"sess_{index}",
                user_id=user_id,
                couple_id=couple_id,
                description=f"第 {index} 条共享",
            )
        )
    monkeypatch.setattr(
        generate_module,
        "extract_semantic",
        lambda _sessions, _couple: (
            {"tags": [{"label": "轻松", "weight": 0.7, "phase": "late"}], "narrative": "微风转晴"},
            [
                {
                    "day": "2026-05-08",
                    "topic": "散步",
                    "user_a_excerpt": "微风",
                    "user_b_excerpt": "晚霞",
                }
            ],
        ),
    )

    report = generate_weekly_report(couple_id, datetime(2026, 5, 11, 0, 0, 0))

    assert report.status == "ready"
    assert report.weather["narrative"] == "微风转晴"
    assert report.resonance[0]["user_a_excerpt"] == "微风"
    assert [stored.report_id for stored in list_reports_for_couple(couple_id)] == [report.report_id]


def test_generate_weekly_report_user_id_leak_persists_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alice_id, bob_id, couple_id = _active_enabled_couple()
    for index, user_id in enumerate([alice_id, bob_id, alice_id], start=1):
        add_session(_session(session_id=f"sess_{index}", user_id=user_id, couple_id=couple_id))
    monkeypatch.setattr(
        generate_module,
        "extract_semantic",
        lambda _sessions, _couple: (
            {"tags": [], "narrative": f"这周 {alice_id} 的节奏更放松"},
            [
                {
                    "day": "2026-05-08",
                    "topic": "散步",
                    "user_a_excerpt": "微风",
                    "user_b_excerpt": "晚霞",
                }
            ],
        ),
    )

    report = generate_weekly_report(couple_id, datetime(2026, 5, 11, 0, 0, 0))

    assert report.status == "failed"
    assert report.weather == {}
    assert report.resonance == []


def test_generate_weekly_report_resonance_uses_couple_user_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = iter(["ffffffff", "11111111", "aaaaaaaa"])
    monkeypatch.setattr(users_repo.uuid, "uuid4", lambda: _FakeUUID(next(ids)))
    user_a_id, user_b_id, couple_id = _active_enabled_couple()
    assert user_a_id > user_b_id

    add_session(
        _session(
            session_id="sess_a1",
            user_id=user_a_id,
            couple_id=couple_id,
            description="A侧晨跑",
        )
    )
    add_session(
        _session(
            session_id="sess_b1",
            user_id=user_b_id,
            couple_id=couple_id,
            description="B侧晚饭",
        )
    )
    add_session(
        _session(
            session_id="sess_a2",
            user_id=user_a_id,
            couple_id=couple_id,
            description="A侧夜谈",
        )
    )

    def fake_extract_resonance(items: list[object]) -> list[ResonanceItem]:
        assert len(items) == 1
        candidate = items[0]
        assert candidate.user_a_text == "A侧晨跑 轻松 A侧夜谈 轻松"
        assert candidate.user_b_text == "B侧晚饭 轻松"
        return [
            ResonanceItem(
                day=candidate.day,
                topic="同日共享",
                user_a_excerpt="A侧",
                user_b_excerpt="B侧",
            )
        ]

    monkeypatch.setattr(
        semantic_module.llm_client,
        "extract_emotions",
        lambda _corpus: [EmotionTag(label="轻松", weight=0.7, phase="middle")],
    )
    monkeypatch.setattr(
        semantic_module.llm_client,
        "compose_weather_narrative",
        lambda _tags: "云层变亮",
    )
    monkeypatch.setattr(semantic_module.llm_client, "extract_resonance", fake_extract_resonance)

    report = generate_weekly_report(couple_id, datetime(2026, 5, 11, 0, 0, 0))

    assert report.status == "ready"
    assert report.resonance[0]["user_a_excerpt"] == "A侧"
    assert report.resonance[0]["user_b_excerpt"] == "B侧"


def test_generate_weekly_report_llm_error_persists_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alice_id, bob_id, couple_id = _active_enabled_couple()
    for index, user_id in enumerate([alice_id, bob_id, alice_id], start=1):
        add_session(_session(session_id=f"sess_{index}", user_id=user_id, couple_id=couple_id))

    def raise_llm(_sessions: list[SessionRecord], _couple: object) -> tuple[dict, list[dict]]:
        raise LLMClientError("bad key")

    monkeypatch.setattr(generate_module, "extract_semantic", raise_llm)

    report = generate_weekly_report(couple_id, datetime(2026, 5, 11, 0, 0, 0))

    assert report.status == "failed"
    assert report.weather == {}
    assert list_reports_for_couple(couple_id)[0].status == "failed"


def test_generate_weekly_report_guard_failure_persists_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alice_id, bob_id, couple_id = _active_enabled_couple()
    for index, user_id in enumerate([alice_id, bob_id, alice_id], start=1):
        add_session(_session(session_id=f"sess_{index}", user_id=user_id, couple_id=couple_id))
    monkeypatch.setattr(
        generate_module,
        "extract_semantic",
        lambda _sessions, _couple: (
            {"tags": [], "narrative": "今天一起做了一顿很香的晚饭"},
            [],
        ),
    )
    monkeypatch.setattr(generate_module, "check_no_verbatim_quote", lambda *_args, **_kwargs: False)

    report = generate_weekly_report(couple_id, datetime(2026, 5, 11, 0, 0, 0))

    assert report.status == "failed"
    assert report.weather == {}
    assert report.resonance == []


def test_semantic_passes_only_allowed_fields_to_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    session = _session(
        session_id="leaky_session_id",
        couple_id="leaky_couple_id",
        files=[{"path": "/tmp/leaky_file.jpg"}],
        description="描述文本",
        feeling="感受文本",
    )

    def fake_extract_emotions(corpus: list[str]) -> list[EmotionTag]:
        seen["corpus"] = corpus
        return [EmotionTag(label="安定", weight=0.6, phase="middle")]

    def fake_compose_weather_narrative(_tags: list[EmotionTag]) -> str:
        return "云层变薄"

    def fake_extract_resonance(items: list[object]) -> list[ResonanceItem]:
        seen["resonance_candidates"] = items
        return []

    monkeypatch.setattr(semantic_module.llm_client, "extract_emotions", fake_extract_emotions)
    monkeypatch.setattr(
        semantic_module.llm_client,
        "compose_weather_narrative",
        fake_compose_weather_narrative,
    )
    monkeypatch.setattr(semantic_module.llm_client, "extract_resonance", fake_extract_resonance)

    couple = Couple(
        couple_id="leaky_couple_id",
        user_a=session.user_id,
        user_b="usr_2",
        created_at="2026-05-08 00:00:00",
        couple_status="active",
        uncouple_initiated_by=None,
        uncouple_initiated_at=None,
        both_agreed_uncouple=False,
        freeze_ends_at=None,
    )

    weather, resonance = semantic_module.extract_semantic([session], couple)

    assert weather["narrative"] == "云层变薄"
    assert resonance == []
    serialized = repr(seen)
    assert "leaky_session_id" not in serialized
    assert "leaky_couple_id" not in serialized
    assert "/tmp/leaky_file.jpg" not in serialized
    assert "描述文本" in serialized
    assert "感受文本" in serialized


def test_semantic_ignores_invalid_content_time_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}
    couple = Couple(
        couple_id="cp_1",
        user_a="usr_a",
        user_b="usr_b",
        created_at="2026-05-08 00:00:00",
        couple_status="active",
        uncouple_initiated_by=None,
        uncouple_initiated_at=None,
        both_agreed_uncouple=False,
        freeze_ends_at=None,
    )
    sessions = [
        _session(
            session_id="invalid_a",
            user_id="usr_a",
            shared_at=None,
            archive_time="",
            upload_time="",
            content_time="上周二",
            description="无效日期 A",
        ),
        _session(
            session_id="invalid_b",
            user_id="usr_b",
            shared_at=None,
            archive_time="",
            upload_time="",
            content_time="上周二",
            description="无效日期 B",
        ),
        _session(
            session_id="valid_a",
            user_id="usr_a",
            shared_at=None,
            archive_time="",
            upload_time="",
            content_time="2026-05-09",
            description="有效日期 A",
        ),
        _session(
            session_id="valid_b",
            user_id="usr_b",
            shared_at=None,
            archive_time="",
            upload_time="",
            content_time="2026-05-09",
            description="有效日期 B",
        ),
    ]

    def fake_extract_resonance(items: list[object]) -> list[ResonanceItem]:
        seen["resonance_candidates"] = items
        return [
            ResonanceItem(
                day=item.day,
                topic=item.topic,
                user_a_excerpt=item.user_a_text,
                user_b_excerpt=item.user_b_text,
            )
            for item in items
        ]

    monkeypatch.setattr(
        semantic_module.llm_client,
        "extract_emotions",
        lambda _corpus: [EmotionTag(label="安定", weight=0.6, phase="middle")],
    )
    monkeypatch.setattr(
        semantic_module.llm_client,
        "compose_weather_narrative",
        lambda _tags: "云层变薄",
    )
    monkeypatch.setattr(semantic_module.llm_client, "extract_resonance", fake_extract_resonance)

    _weather, resonance = semantic_module.extract_semantic(sessions, couple)

    candidates = seen["resonance_candidates"]
    assert [candidate.day for candidate in candidates] == ["2026-05-09"]
    assert resonance == [
        {
            "day": "2026-05-09",
            "topic": "同日共享",
            "user_a_excerpt": "有效日期 A 轻",
            "user_b_excerpt": "有效日期 B 轻",
        }
    ]
