"""Pure scheduling decisions for weekly report generation."""

from __future__ import annotations

from datetime import datetime, timedelta

from backend.domain.models import Couple
from backend.infrastructure.database.db import parse_dt

_RETRY_CONSUMED_KEY = "_weekly_report_retry_consumed"


def _as_dt(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return parse_dt(value)
    return None


def _user_enabled(db: dict, user_id: str) -> bool:
    for user in db.get("users", []):
        if user.get("user_id") == user_id:
            return bool(user.get("weekly_report_enabled", False))
    return False


def _interval(couple: Couple) -> timedelta:
    return timedelta(days=max(1, int(couple.weekly_report_interval_days)))


def _reports_for_couple(couple_id: str, db: dict) -> list[dict]:
    return [report for report in db.get("reports", []) if report.get("couple_id") == couple_id]


def _latest_report(couple_id: str, db: dict) -> dict | None:
    reports = _reports_for_couple(couple_id, db)
    if not reports:
        return None

    def sort_key(report: dict) -> tuple[datetime, datetime]:
        return (
            _as_dt(report.get("window_end")) or datetime.min,
            _as_dt(report.get("generated_at")) or datetime.min,
        )

    return max(reports, key=sort_key)


def previous_report_window_end(couple_id: str, db: dict) -> datetime | None:
    """Return the latest persisted window_end for a couple's reports."""

    latest = _latest_report(couple_id, db)
    if not latest:
        return None
    return _as_dt(latest.get("window_end"))


def should_generate_for_couple(couple: Couple, db: dict, now: datetime) -> bool:
    """Return whether a couple should receive a weekly report on this tick."""

    if couple.couple_status != "active":
        return False

    if not (_user_enabled(db, couple.user_a) and _user_enabled(db, couple.user_b)):
        return False

    latest = _latest_report(couple.couple_id, db)
    if latest and latest.get("status") == "failed":
        consumed = db.get(_RETRY_CONSUMED_KEY, set())
        if latest.get("report_id") not in consumed:
            return True

    previous_end = previous_report_window_end(couple.couple_id, db)
    if previous_end:
        return now >= previous_end + _interval(couple)

    anchor = _as_dt(couple.created_at)
    return bool(anchor and now >= anchor + _interval(couple))
