"""Session field validation helpers."""

from __future__ import annotations

from pathlib import Path

from backend.config.settings import FIELD_SCHEMA, TEXT_EXTS


def is_text_session(session: dict) -> bool:
    if session.get("source_type") == "text":
        return True
    exts = {
        Path(file_record["filename"]).suffix.lower() for file_record in session.get("files", [])
    }
    return bool(exts) and exts.issubset(TEXT_EXTS)


def validate_session(session: dict) -> list[str]:
    skip = {"description"} if is_text_session(session) else set()
    return [
        field["label"]
        for field in FIELD_SCHEMA
        if field["required"]
        and field["key"] not in skip
        and not str(session.get(field["key"], "")).strip()
    ]
