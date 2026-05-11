"""Weekly report generation use case."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from backend.application.reports.errors import ReportGenerationError
from backend.application.reports.guard import check_no_verbatim_quote
from backend.application.reports.metrics import compute_footprint, compute_suspense
from backend.application.reports.policies import service_active_for_couple
from backend.application.reports.semantic import extract_semantic
from backend.domain.models import Report, SessionRecord
from backend.infrastructure.ai.agent_skills import get_shared_sessions_for_rag
from backend.infrastructure.ai.llm_client import DEEPSEEK_MODEL, LLMClientError
from backend.infrastructure.database.couples_repo import get_couple_by_id
from backend.infrastructure.database.reports_repo import create_report, get_report, update_report

logger = logging.getLogger(__name__)

_SPARSE_SESSION_THRESHOLD = 3


def _fmt(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _source_session_ids(sessions: list[SessionRecord]) -> list[str]:
    return [session.session_id for session in sessions]


def _report_id(couple_id: str, window_end: datetime) -> str:
    return f"rpt_{window_end.strftime('%Y%m%d')}_{couple_id}"


def _persist(report: Report) -> Report:
    if get_report(report.report_id):
        update_report(report)
    else:
        create_report(report)
    return report


def _compose_report(
    *,
    couple_id: str,
    window: tuple[datetime, datetime],
    generated_at: datetime,
    sessions: list[SessionRecord],
    footprint: dict,
    weather: dict,
    resonance: list[dict],
    suspense: list[dict],
    status: str,
) -> Report:
    window_start, window_end = window
    return Report(
        report_id=_report_id(couple_id, window_end),
        couple_id=couple_id,
        window_start=_fmt(window_start),
        window_end=_fmt(window_end),
        generated_at=_fmt(generated_at),
        model_version=DEEPSEEK_MODEL,
        footprint=footprint,
        weather=weather,
        resonance=resonance,
        suspense=suspense,
        status=status,
        source_session_ids=_source_session_ids(sessions),
    )


def generate_weekly_report(
    couple_id: str,
    window_end: datetime | None = None,
) -> Report:
    """Generate and persist a weekly report for a couple."""

    if not service_active_for_couple(couple_id):
        raise ReportGenerationError("weekly report service is not active for this couple")

    couple = get_couple_by_id(couple_id)
    if not couple:
        raise ReportGenerationError("couple does not exist")

    end = window_end or datetime.now()
    window = (end - timedelta(days=couple.weekly_report_interval_days), end)
    raw_sessions = get_shared_sessions_for_rag(couple_id, window)
    sessions = [SessionRecord.from_dict(raw_session) for raw_session in raw_sessions]
    footprint = compute_footprint(sessions, window)
    suspense = compute_suspense(couple_id, end)
    generated_at = datetime.now()

    if len(sessions) < _SPARSE_SESSION_THRESHOLD:
        return _persist(
            _compose_report(
                couple_id=couple_id,
                window=window,
                generated_at=generated_at,
                sessions=sessions,
                footprint=footprint,
                weather={},
                resonance=[],
                suspense=suspense,
                status="sparse",
            )
        )

    try:
        weather, resonance = extract_semantic(sessions)
    except LLMClientError:
        logger.exception("LLMClientError while generating weekly report for %s", couple_id)
        return _persist(
            _compose_report(
                couple_id=couple_id,
                window=window,
                generated_at=generated_at,
                sessions=sessions,
                footprint=footprint,
                weather={},
                resonance=[],
                suspense=suspense,
                status="failed",
            )
        )

    payload = {
        "footprint": footprint,
        "weather": weather,
        "resonance": resonance,
        "suspense": suspense,
    }
    status = "ready" if check_no_verbatim_quote(payload, sessions) else "failed"
    if status == "failed":
        logger.warning("Weekly report failed verbatim quote guard for %s", couple_id)

    return _persist(
        _compose_report(
            couple_id=couple_id,
            window=window,
            generated_at=generated_at,
            sessions=sessions,
            footprint=footprint,
            weather=weather if status == "ready" else {},
            resonance=resonance if status == "ready" else [],
            suspense=suspense,
            status=status,
        )
    )
