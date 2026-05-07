"""Session editing and archiving workflows."""

from __future__ import annotations

import shutil
from pathlib import Path

from backend.application.sessions.markdown import write_session_markdown
from backend.application.sessions.validation import is_text_session, validate_session
from backend.config.settings import FIELD_SCHEMA, FINAL_DIR
from backend.infrastructure.database.db import now_str
from backend.infrastructure.database.sessions_repo import get_session_by_id, replace_session


def move_to_final(session_id: str) -> None:
    session = get_session_by_id(session_id)
    if not session:
        return

    new_files = []
    for file_record in session.files:
        src = Path(file_record["path"])
        dst = FINAL_DIR / src.name
        if src.exists():
            shutil.move(str(src), str(dst))
        file_record["path"] = str(dst)
        new_files.append(file_record)
    session.files = new_files
    session.status = "final"
    session.archive_time = now_str()
    session.is_complete = True
    replace_session(session)
    write_session_markdown(session.to_dict())


def update_session_fields(session_id: str, new_values: dict) -> None:
    session = get_session_by_id(session_id)
    if not session:
        return
    valid_keys = {field["key"] for field in FIELD_SCHEMA}
    session_dict = session.to_dict()
    if session.status == "final":
        changes = {}
        for key, value in new_values.items():
            if key in valid_keys and session_dict.get(key) != value:
                if key == "description" and is_text_session(session_dict):
                    continue
                changes[key] = {"from": session_dict.get(key, ""), "to": value}
        if changes:
            session.edit_history.append({"edited_at": now_str(), "changes": changes})
    for key, value in new_values.items():
        if key in valid_keys:
            setattr(session, key, value)
    session.is_complete = not validate_session(session.to_dict())
    replace_session(session)
    if session.status == "final":
        write_session_markdown(session.to_dict())
