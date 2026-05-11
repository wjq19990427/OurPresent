"""Report repository backed by the local JSON database."""

from __future__ import annotations

from backend.domain.models import Report
from backend.infrastructure.database.db import load_db, save_db


def create_report(report: Report) -> None:
    db = load_db()
    db["reports"].append(report.to_dict())
    save_db(db)


def get_report(report_id: str) -> Report | None:
    db = load_db()
    for raw_report in db["reports"]:
        if raw_report["report_id"] == report_id:
            return Report.from_dict(raw_report)
    return None


def list_reports_for_couple(couple_id: str) -> list[Report]:
    db = load_db()
    reports = [
        Report.from_dict(raw_report)
        for raw_report in db["reports"]
        if raw_report["couple_id"] == couple_id
    ]
    return sorted(reports, key=lambda report: report.generated_at, reverse=True)


def update_report(report: Report) -> None:
    db = load_db()
    for index, raw_report in enumerate(db["reports"]):
        if raw_report["report_id"] == report.report_id:
            db["reports"][index] = report.to_dict()
            break
    save_db(db)


def delete_reports_for_couple(couple_id: str) -> int:
    db = load_db()
    before_count = len(db["reports"])
    db["reports"] = [
        raw_report for raw_report in db["reports"] if raw_report.get("couple_id") != couple_id
    ]
    save_db(db)
    return before_count - len(db["reports"])
