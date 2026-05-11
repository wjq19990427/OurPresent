"""
Phase 2 AI interface placeholders.
"""

from __future__ import annotations

from datetime import datetime

from backend.infrastructure.database.db import load_db, parse_dt


def get_shared_sessions_for_rag(
    couple_id: str,
    window: tuple[datetime, datetime] | None = None,
) -> list[dict]:
    db = load_db()
    sessions = []
    for session in db["sessions"]:
        if session.get("couple_id") != couple_id or session.get("visibility") != "shared":
            continue
        if window:
            shared_at = parse_dt(session.get("shared_at") or "")
            if not shared_at or not (window[0] <= shared_at <= window[1]):
                continue
        sessions.append(session)
    return sessions


def get_report_history(couple_id: str) -> list[dict]:
    from backend.application.reports.query import list_reports

    return [report.to_dict() for report in list_reports(couple_id)]
