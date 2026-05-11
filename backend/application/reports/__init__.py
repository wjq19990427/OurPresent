"""Application services for relationship reports."""

from backend.application.reports.errors import ReportGenerationError
from backend.application.reports.generate import generate_weekly_report
from backend.application.reports.guard import check_no_verbatim_quote
from backend.application.reports.metrics import compute_footprint, compute_suspense
from backend.application.reports.policies import partner_enabled_status, service_active_for_couple
from backend.application.reports.query import get_latest_ready_report, get_report, list_reports
from backend.application.reports.semantic import extract_semantic

__all__ = [
    "compute_footprint",
    "compute_suspense",
    "check_no_verbatim_quote",
    "extract_semantic",
    "generate_weekly_report",
    "get_latest_ready_report",
    "get_report",
    "list_reports",
    "partner_enabled_status",
    "ReportGenerationError",
    "service_active_for_couple",
]
