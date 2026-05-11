"""
Phase 2 AI interface placeholders.
"""

from __future__ import annotations

from backend.application.reports import list_reports
from backend.infrastructure.database.db import load_db


def get_shared_sessions_for_rag(couple_id: str) -> list[dict]:
    db = load_db()
    return [
        session
        for session in db["sessions"]
        if session.get("couple_id") == couple_id and session.get("visibility") == "shared"
    ]


def get_report_history(couple_id: str) -> list[dict]:
    return [report.to_dict() for report in list_reports(couple_id)]
