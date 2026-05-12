"""Pure metric helpers for relationship reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from backend.domain.models import SessionRecord
from backend.infrastructure.database.db import parse_dt
from backend.infrastructure.database.sessions_repo import list_sessions_for_couple

_PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif"}
_VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
_TEXT_EXTS = {".txt", ".md", ".rst"}


def _file_ext(file_record: dict) -> str:
    name = (
        file_record.get("original_name")
        or file_record.get("filename")
        or file_record.get("path")
        or ""
    )
    return Path(str(name)).suffix.lower()


def _session_kind(session: SessionRecord) -> str:
    if session.source_type == "text" or not session.files:
        return "text"

    exts = {_file_ext(file_record) for file_record in session.files}
    if exts & _VIDEO_EXTS:
        return "video"
    if exts & _PHOTO_EXTS:
        return "photo"
    if exts and exts.issubset(_TEXT_EXTS):
        return "text"
    return "text"


def _require_shared_at(session: SessionRecord) -> datetime:
    if not session.shared_at:
        raise ValueError(
            "compute_footprint requires every session to include shared_at; "
            f"missing for session_id={session.session_id}"
        )
    parsed = parse_dt(session.shared_at)
    if parsed is None:
        raise ValueError(
            "compute_footprint requires every session.shared_at to be parseable; "
            f"invalid for session_id={session.session_id}"
        )
    return parsed


def _session_day(session: SessionRecord) -> str | None:
    parsed = parse_dt(session.shared_at or "")
    return parsed.strftime("%Y-%m-%d") if parsed else None


def compute_footprint(sessions: list[SessionRecord], window: tuple[datetime, datetime]) -> dict:
    """Compute structured footprint metrics for shared sessions in a report window."""

    window_start, window_end = window
    filtered = []
    for session in sessions:
        shared_at = _require_shared_at(session)
        if window_start <= shared_at <= window_end:
            filtered.append(session)

    by_kind = {"photo": 0, "video": 0, "text": 0}
    by_author: dict[str, int] = {}
    active_days = set()
    comment_count = 0

    for session in filtered:
        kind = _session_kind(session)
        by_kind[kind] = by_kind.get(kind, 0) + 1
        by_author[session.user_id] = by_author.get(session.user_id, 0) + 1
        comment_count += len(session.comments)
        if day := _session_day(session):
            active_days.add(day)

    return {
        "total": len(filtered),
        "by_kind": by_kind,
        "active_days": len(active_days),
        "comment_count": comment_count,
        "by_author": by_author,
    }


def _days_remaining(unlock_at: datetime | None, now: datetime) -> int:
    if not unlock_at:
        return 0
    remaining_seconds = (unlock_at - now).total_seconds()
    if remaining_seconds <= 0:
        return 0
    return int((remaining_seconds + 86399) // 86400)


def compute_suspense(couple_id: str, now: datetime) -> list[dict]:
    """Return pending-unlock metadata for a couple, ordered by unlock time."""

    pending = [
        session
        for session in list_sessions_for_couple(couple_id)
        if session.visibility == "pending_unlock"
    ]
    pending.sort(key=lambda session: parse_dt(session.unlock_at or "") or datetime.max)

    return [
        {
            "session_id": session.session_id,
            "unlock_at": session.unlock_at,
            "days_remaining": _days_remaining(parse_dt(session.unlock_at or ""), now),
            "kind": _session_kind(session),
        }
        for session in pending
    ]
