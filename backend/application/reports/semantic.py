"""LLM-backed semantic extraction for weekly reports."""

from __future__ import annotations

from collections import defaultdict

from backend.domain.models import SessionRecord
from backend.infrastructure.ai import llm_client
from backend.infrastructure.ai.llm_client import EmotionTag, ResonanceCandidate, ResonanceItem
from backend.infrastructure.database.db import parse_dt


def _session_day(session: SessionRecord) -> str:
    parsed = parse_dt(session.shared_at or session.archive_time or session.upload_time)
    if parsed:
        return parsed.strftime("%Y-%m-%d")
    return (session.content_time or "")[:10]


def _corpus_item(session: SessionRecord) -> str:
    fields = {
        "description": session.description,
        "feeling": session.feeling,
        "content_time": session.content_time,
        "user_id": session.user_id,
    }
    return "\n".join(f"{key}: {value}" for key, value in fields.items() if value)


def _candidate_text(session: SessionRecord) -> str:
    return " ".join(part for part in (session.description, session.feeling) if part)


def _resonance_candidates(sessions: list[SessionRecord]) -> list[ResonanceCandidate]:
    by_day: dict[str, dict[str, list[SessionRecord]]] = defaultdict(lambda: defaultdict(list))
    for session in sessions:
        by_day[_session_day(session)][session.user_id].append(session)

    candidates: list[ResonanceCandidate] = []
    for day, by_user in by_day.items():
        if len(by_user) < 2:
            continue
        user_ids = sorted(by_user)
        first_user, second_user = user_ids[0], user_ids[1]
        first_text = " ".join(_candidate_text(session) for session in by_user[first_user])
        second_text = " ".join(_candidate_text(session) for session in by_user[second_user])
        if first_text and second_text:
            candidates.append(
                ResonanceCandidate(
                    day=day,
                    topic="同日共享",
                    user_a_text=first_text[:500],
                    user_b_text=second_text[:500],
                )
            )
    return candidates


def _tags_to_dict(tags: list[EmotionTag]) -> list[dict]:
    return [{"label": tag.label, "weight": tag.weight, "phase": tag.phase} for tag in tags]


def _resonance_to_dict(items: list[ResonanceItem]) -> list[dict]:
    return [
        {
            "day": item.day,
            "topic": item.topic,
            "user_a_excerpt": item.user_a_excerpt[:8],
            "user_b_excerpt": item.user_b_excerpt[:8],
        }
        for item in items
    ]


def extract_semantic(sessions: list[SessionRecord]) -> tuple[dict, list[dict]]:
    """Extract weather and resonance modules from shared sessions."""

    corpus = [_corpus_item(session) for session in sessions]
    tags = llm_client.extract_emotions(corpus)
    narrative = llm_client.compose_weather_narrative(tags)
    resonance = llm_client.extract_resonance(_resonance_candidates(sessions))

    return (
        {"tags": _tags_to_dict(tags), "narrative": narrative[:80]},
        _resonance_to_dict(resonance),
    )
