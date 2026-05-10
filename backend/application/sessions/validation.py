"""Session field validation helpers."""

from __future__ import annotations

from pathlib import Path

from backend.config.settings import FIELD_SCHEMA, TEXT_EXTS
from backend.domain.models import SessionRecord


def is_text_session(session: SessionRecord) -> bool:
    if session.source_type == "text":
        return True
    exts = {
        Path(file_record["filename"]).suffix.lower()
        for file_record in session.files
    }
    return bool(exts) and exts.issubset(TEXT_EXTS)


def validate_session(session: SessionRecord) -> list[str]:
    skip = {"description"} if is_text_session(session) else set()
    return [
        field["label"]
        for field in FIELD_SCHEMA
        if field["required"]
        and field["key"] not in skip
        and not str(getattr(session, field["key"], "")).strip()
    ]
