"""Session creation workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.application.sessions.files import write_session_files
from backend.application.sessions.markdown import write_session_markdown
from backend.application.sessions.validation import validate_session
from backend.config.settings import FIELD_SCHEMA, FINAL_DIR, PENDING_DIR
from backend.domain.models import SessionRecord
from backend.infrastructure.database.db import now_str
from backend.infrastructure.database.sessions_repo import add_session


def _build_session_base(user_id: str, couple_id: Optional[str]) -> SessionRecord:
    now = datetime.now()
    session_id = now.strftime("%Y%m%d_%H%M%S")
    return SessionRecord(
        session_id=session_id,
        user_id=user_id,
        couple_id=couple_id,
        status="pending",
        visibility="private",
        unlock_requested_at=None,
        shared_at=None,
        upload_time=now.strftime("%Y-%m-%d %H:%M:%S"),
        archive_time="",
        is_complete=False,
    )


def save_session_pending(
    user_id: str,
    couple_id: Optional[str],
    file_data_list: list[tuple[bytes, str]],
    source_type: str,
    field_values: dict,
) -> None:
    session = _build_session_base(user_id, couple_id)
    session.source_type = source_type
    for key, value in field_values.items():
        if key in {field["key"] for field in FIELD_SCHEMA}:
            setattr(session, key, value)
    session.files = write_session_files(session.session_id, file_data_list, PENDING_DIR)
    session.is_complete = not validate_session(session)
    add_session(session)


def save_session_final(
    user_id: str,
    couple_id: Optional[str],
    file_data_list: list[tuple[bytes, str]],
    source_type: str,
    field_values: dict,
) -> None:
    session = _build_session_base(user_id, couple_id)
    session.source_type = source_type
    session.status = "final"
    session.archive_time = now_str()
    for key, value in field_values.items():
        if key in {field["key"] for field in FIELD_SCHEMA}:
            setattr(session, key, value)
    session.files = write_session_files(session.session_id, file_data_list, FINAL_DIR)
    session.is_complete = True
    add_session(session)
    write_session_markdown(session)
