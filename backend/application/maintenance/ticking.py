"""State transitions for time locks, frozen couples, auth tokens, and reports."""

from __future__ import annotations

import logging
from datetime import datetime

from backend.application.reports.generate import generate_weekly_report
from backend.application.reports.scheduling import should_generate_for_couple
from backend.application.sessions.destruction import destroy_couple_data_in_db
from backend.domain.models import Couple, Report
from backend.infrastructure.database.db import load_db, now_str, parse_dt, save_db

logger = logging.getLogger(__name__)

_RETRY_CONSUMED_KEY = "_weekly_report_retry_consumed"
_failed_retry_consumed_report_ids: set[str] = set()


def _sync_retry_state(db: dict) -> None:
    db[_RETRY_CONSUMED_KEY] = set(_failed_retry_consumed_report_ids)


def _latest_report(couple_id: str, db: dict) -> dict | None:
    reports = [report for report in db.get("reports", []) if report.get("couple_id") == couple_id]
    if not reports:
        return None

    def sort_key(report: dict) -> tuple[datetime, datetime]:
        return (
            parse_dt(report.get("window_end", "")) or datetime.min,
            parse_dt(report.get("generated_at", "")) or datetime.min,
        )

    return max(reports, key=sort_key)


def _upsert_report(db: dict, report: Report) -> None:
    stored = report.to_dict()
    for index, existing in enumerate(db.setdefault("reports", [])):
        if existing.get("report_id") == report.report_id:
            db["reports"][index] = stored
            return
    db["reports"].append(stored)


def _mark_retry_state(couple_id: str, db: dict, report: Report, was_retry: bool) -> None:
    if report.status == "failed":
        if was_retry:
            _failed_retry_consumed_report_ids.add(report.report_id)
        return

    for raw_report in db.get("reports", []):
        if raw_report.get("couple_id") == couple_id:
            report_id = raw_report.get("report_id")
            if report_id:
                _failed_retry_consumed_report_ids.discard(report_id)


def tick(db: dict) -> bool:
    now = datetime.now()
    changed = False

    for session in db["sessions"]:
        if session.get("visibility") == "pending_unlock":
            unlock_dt = parse_dt(session.get("unlock_at", ""))
            if unlock_dt and unlock_dt <= now:
                session["visibility"] = "shared"
                session["shared_at"] = now_str()
                changed = True

    for couple in db["couples"]:
        if couple.get("couple_status") == "frozen" and couple.get("freeze_ends_at"):
            ends = parse_dt(couple["freeze_ends_at"])
            if ends and now >= ends:
                destroy_couple_data_in_db(db, couple["couple_id"])
                changed = True

    before = len(db.get("auth_tokens", []))
    db["auth_tokens"] = [
        token
        for token in db.get("auth_tokens", [])
        if parse_dt(token.get("expires_at", "")) and parse_dt(token["expires_at"]) > now
    ]
    if len(db["auth_tokens"]) != before:
        changed = True

    _sync_retry_state(db)
    for raw_couple in db.get("couples", []):
        couple = Couple.from_dict(raw_couple)
        previous = _latest_report(couple.couple_id, db)
        was_retry = bool(
            previous
            and previous.get("status") == "failed"
            and previous.get("report_id") not in _failed_retry_consumed_report_ids
        )
        if not should_generate_for_couple(couple, db, now):
            continue

        try:
            report = generate_weekly_report(couple.couple_id, now)
        except Exception:
            logger.exception("Weekly report generation failed during tick for %s", couple.couple_id)
            continue

        _upsert_report(db, report)
        _mark_retry_state(couple.couple_id, db, report, was_retry)
        db[_RETRY_CONSUMED_KEY] = set(_failed_retry_consumed_report_ids)
        changed = True

    return changed


def load_db_with_tick() -> dict:
    db = load_db()
    if tick(db):
        save_db(db)
        db = load_db()
    return db
