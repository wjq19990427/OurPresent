"""
Session 字段校验工具。
"""

from __future__ import annotations

from pathlib import Path

from core.config import FIELD_SCHEMA, TEXT_EXTS


def _is_text_session(session: dict) -> bool:
    """判断是否为纯文字记录（source_type=="text" 或全部文件均为 txt/md）。"""
    if session.get("source_type") == "text":
        return True
    exts = {Path(f["filename"]).suffix.lower() for f in session.get("files", [])}
    return bool(exts) and exts.issubset(TEXT_EXTS)


def validate_session(session: dict) -> list[str]:
    """返回未填写的必填字段 label 列表；空列表表示信息完整。"""
    skip = {"description"} if _is_text_session(session) else set()
    return [
        f["label"]
        for f in FIELD_SCHEMA
        if f["required"] and f["key"] not in skip
        and not str(session.get(f["key"], "")).strip()
    ]
