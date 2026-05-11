"""Read use cases for relationship reports."""

from __future__ import annotations

from backend.domain.models import Report
from backend.infrastructure.database import reports_repo

_VISIBLE_REPORT_STATUSES = {"ready", "sparse"}


def list_reports(couple_id: str) -> list[Report]:
    return reports_repo.list_reports_for_couple(couple_id)


def get_latest_ready_report(couple_id: str) -> Report | None:
    for report in list_reports(couple_id):
        if report.status in _VISIBLE_REPORT_STATUSES:
            return report
    return None


def get_report(report_id: str) -> Report | None:
    return reports_repo.get_report(report_id)
