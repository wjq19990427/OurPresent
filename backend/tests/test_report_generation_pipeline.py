from __future__ import annotations

from datetime import datetime

import pytest

from backend.application.couples import accept_bind, send_bind_request
from backend.application.reports import check_no_verbatim_quote, generate_weekly_report
from backend.application.reports import generate as generate_module
from backend.application.reports import semantic as semantic_module
from backend.domain.models import SessionRecord
from backend.infrastructure.ai.llm_client import EmotionTag, LLMClientError, ResonanceItem
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


def test_generate_weekly_report_sparse_skips_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    alice_id, _, couple_id = _active_enabled_couple()
    add_session(_session(session_id="sess_1", user_id=alice_id, couple_id=couple_id))
    monkeypatch.setattr(
        generate_module,
        "extract_semantic",
        lambda _sessions: pytest.fail("sparse reports must not call LLM"),
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
        lambda _sessions: (
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


def test_generate_weekly_report_llm_error_persists_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alice_id, bob_id, couple_id = _active_enabled_couple()
    for index, user_id in enumerate([alice_id, bob_id, alice_id], start=1):
        add_session(_session(session_id=f"sess_{index}", user_id=user_id, couple_id=couple_id))

    def raise_llm(_sessions: list[SessionRecord]) -> tuple[dict, list[dict]]:
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
        lambda _sessions: ({"tags": [], "narrative": "今天一起做了一顿很香的晚饭"}, []),
    )
    monkeypatch.setattr(generate_module, "check_no_verbatim_quote", lambda *_args: False)

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

    weather, resonance = semantic_module.extract_semantic([session])

    assert weather["narrative"] == "云层变薄"
    assert resonance == []
    serialized = repr(seen)
    assert "leaky_session_id" not in serialized
    assert "leaky_couple_id" not in serialized
    assert "/tmp/leaky_file.jpg" not in serialized
    assert "描述文本" in serialized
    assert "感受文本" in serialized
