"""Session editing and archiving workflows."""

from __future__ import annotations

import shutil
from pathlib import Path

from backend.application.sessions.markdown import write_session_markdown
from backend.application.sessions.validation import is_text_session, validate_session
from backend.config.settings import FIELD_SCHEMA, FINAL_DIR
from backend.infrastructure.database.db import now_str
from backend.infrastructure.database.sessions_repo import get_session_by_id, replace_session

_APPENDABLE_TEXT_FIELDS = {
    field["key"] for field in FIELD_SCHEMA if field.get("type") == "textarea"
}


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
    write_session_markdown(session)


def update_session_fields(session_id: str, new_values: dict) -> None:
    session = get_session_by_id(session_id)
    if not session:
        return
    valid_keys = {field["key"] for field in FIELD_SCHEMA}
    if session.status == "final":
        changes = {}
        for key, value in new_values.items():
            old_value = getattr(session, key, "")
            if key in valid_keys and old_value != value:
                if key == "description" and is_text_session(session):
                    continue
                changes[key] = {"from": old_value, "to": value}
        if changes:
            session.edit_history.append({"edited_at": now_str(), "changes": changes})
    for key, value in new_values.items():
        if key in valid_keys:
            setattr(session, key, value)
    session.is_complete = not validate_session(session)
    replace_session(session)
    if session.status == "final":
        write_session_markdown(session)


def append_to_session(session_id: str, field: str, text: str) -> None:
    session = get_session_by_id(session_id)
    if not session or session.visibility != "pending_unlock":
        raise ValueError("session must be pending_unlock")
    if field not in _APPENDABLE_TEXT_FIELDS:
        raise ValueError("field is not appendable")
    appended_text = text.strip()
    if not appended_text:
        raise ValueError("append text cannot be empty")

    original = getattr(session, field, "")
    marker = f"[追加于 {now_str()}]"
    if original:
        next_value = f"{original}\n\n---\n{marker}\n{appended_text}"
    else:
        next_value = f"{marker}\n{appended_text}"
    setattr(session, field, next_value)
    session.is_complete = not validate_session(session)
    replace_session(session)
    if session.status == "final":
        write_session_markdown(session)
