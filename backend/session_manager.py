"""
Session 生命周期管理：创建、归档、评论、可见性控制、数据销毁、解绑协议。
"""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.config import FIELD_SCHEMA, PENDING_DIR, FINAL_DIR
from utils.validators import validate_session, _is_text_session
from utils.file_processor import write_files
from backend.db_manager import (
    load_db, save_db, _now_str, _parse_dt,
    get_couple_for_user, _update_couple,
)


# ── Session 构建 ──────────────────────────────────────────────────────────

def _build_session_base(user_id: str, couple_id: Optional[str]) -> dict:
    now = datetime.now()
    sid = now.strftime("%Y%m%d_%H%M%S")
    return {
        "session_id":          sid,
        "user_id":             user_id,
        "couple_id":           couple_id,
        "status":              "pending",
        "visibility":          "private",
        "unlock_requested_at": None,
        "shared_at":           None,
        "upload_time":         now.strftime("%Y-%m-%d %H:%M:%S"),
        "archive_time":        "",
        "is_complete":         False,
        "edit_history":        [],
        "files":               [],
        "source_type":         "file",
        "content_time":        "",
        "description":         "",
        "feeling":             "",
        "reason":              "",
        "comments":            [],
    }


# ── 文件辅助 ──────────────────────────────────────────────────────────────

def _delete_session_files(session: dict) -> None:
    for f in session.get("files", []):
        p = Path(f.get("path", ""))
        if p.exists():
            p.unlink(missing_ok=True)
    md = FINAL_DIR / f"{session['session_id']}.md"
    md.unlink(missing_ok=True)


def _write_md(session: dict) -> None:
    names = [f["original_name"] for f in session.get("files", [])]
    title = names[0] if names else session["session_id"]
    count = len(names)
    lines = [
        f"# {title}（共 {count} 个文件）\n",
        f"**上传时间**：{session.get('upload_time', '')}\n",
        f"**归档时间**：{session.get('archive_time', '')}\n",
    ]
    for field in FIELD_SCHEMA:
        val = session.get(field["key"], "")
        if val:
            lines += [f"\n## {field['label']}\n", f"{val}\n"]

    comments = session.get("comments", [])
    if comments:
        lines.append("\n---\n\n## 评论区\n")
        for c in comments:
            lines += [f"\n**{c['created_at']}**\n\n{c['text']}\n"]

    history = session.get("edit_history", [])
    if history:
        lines.append("\n---\n\n## 编辑历史\n")
        for h in reversed(history):
            lines.append(f"\n### {h['edited_at']}\n")
            for k, v in h["changes"].items():
                label = next((f["label"] for f in FIELD_SCHEMA if f["key"] == k), k)
                lines.append(f"- **{label}**：「{v['from']}」→「{v['to']}」\n")

    md_path = FINAL_DIR / f"{session['session_id']}.md"
    md_path.write_text("".join(lines), encoding="utf-8")


# ── Session 生命周期 ──────────────────────────────────────────────────────

def save_session_pending(
    user_id: str,
    couple_id: Optional[str],
    file_data_list: list[tuple[bytes, str]],
    source_type: str,
    field_values: dict,
) -> None:
    db = load_db()
    s = _build_session_base(user_id, couple_id)
    s["source_type"] = source_type
    s.update({k: v for k, v in field_values.items() if k in {f["key"] for f in FIELD_SCHEMA}})
    s["files"] = write_files(s["session_id"], file_data_list, PENDING_DIR)
    s["is_complete"] = not validate_session(s)
    db["sessions"].append(s)
    save_db(db)


def save_session_final(
    user_id: str,
    couple_id: Optional[str],
    file_data_list: list[tuple[bytes, str]],
    source_type: str,
    field_values: dict,
) -> None:
    db = load_db()
    s = _build_session_base(user_id, couple_id)
    s["source_type"]  = source_type
    s["status"]       = "final"
    s["archive_time"] = _now_str()
    s.update({k: v for k, v in field_values.items() if k in {f["key"] for f in FIELD_SCHEMA}})
    s["files"] = write_files(s["session_id"], file_data_list, FINAL_DIR)
    s["is_complete"] = True
    db["sessions"].append(s)
    save_db(db)
    _write_md(s)


def move_to_final(session_id: str) -> None:
    db = load_db()
    for s in db["sessions"]:
        if s["session_id"] == session_id:
            new_files = []
            for f in s["files"]:
                src = Path(f["path"])
                dst = FINAL_DIR / src.name
                if src.exists():
                    shutil.move(str(src), str(dst))
                f["path"] = str(dst)
                new_files.append(f)
            s["files"]        = new_files
            s["status"]       = "final"
            s["archive_time"] = _now_str()
            s["is_complete"]  = True
            save_db(db)
            _write_md(s)
            return


def update_session_fields(session_id: str, new_values: dict) -> None:
    db = load_db()
    for s in db["sessions"]:
        if s["session_id"] != session_id:
            continue
        valid_keys = {f["key"] for f in FIELD_SCHEMA}
        if s["status"] == "final":
            changes = {}
            for k, v in new_values.items():
                if k in valid_keys and s.get(k) != v:
                    if k == "description" and _is_text_session(s):
                        continue
                    changes[k] = {"from": s.get(k, ""), "to": v}
            if changes:
                s["edit_history"].append({
                    "edited_at": _now_str(),
                    "changes":   changes,
                })
        for k, v in new_values.items():
            if k in valid_keys:
                s[k] = v
        s["is_complete"] = not validate_session(s)
        save_db(db)
        if s["status"] == "final":
            _write_md(s)
        return


# ── 可见性控制（时间锁）──────────────────────────────────────────────────

def request_unlock(session_id: str) -> None:
    db = load_db()
    for s in db["sessions"]:
        if s["session_id"] == session_id and s.get("visibility") == "private":
            s["visibility"]          = "pending_unlock"
            s["unlock_requested_at"] = _now_str()
            break
    save_db(db)


def revoke_unlock(session_id: str) -> None:
    db = load_db()
    for s in db["sessions"]:
        if s["session_id"] == session_id and s.get("visibility") == "pending_unlock":
            s["visibility"]          = "private"
            s["unlock_requested_at"] = None
            break
    save_db(db)


# ── 评论 CRUD ─────────────────────────────────────────────────────────────

def add_comment(session_id: str, author_id: str, text: str) -> None:
    db = load_db()
    for s in db["sessions"]:
        if s["session_id"] == session_id:
            now = datetime.now()
            s["comments"].append({
                "id":         now.strftime("%Y%m%d_%H%M%S_") + str(now.microsecond),
                "author":     author_id,
                "text":       text,
                "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            })
            save_db(db)
            if s["status"] == "final":
                _write_md(s)
            return


def delete_comment(session_id: str, comment_id: str) -> None:
    db = load_db()
    for s in db["sessions"]:
        if s["session_id"] == session_id:
            s["comments"] = [c for c in s["comments"] if c["id"] != comment_id]
            save_db(db)
            if s["status"] == "final":
                _write_md(s)
            return


# ── 数据导出 ──────────────────────────────────────────────────────────────

def collect_export_files(user_id: str) -> list[Path]:
    """返回该用户可导出的文件路径列表（仅自己的 session 文件）。"""
    db = load_db()
    paths: list[Path] = []
    for s in db["sessions"]:
        if s.get("user_id") != user_id:
            continue
        for f in s.get("files", []):
            p = Path(f.get("path", ""))
            if p.exists():
                paths.append(p)
    return paths


# ── 数据销毁 ──────────────────────────────────────────────────────────────

def destroy_couple_data(couple_id: str) -> None:
    """销毁情侣关系的全部数据（sessions + 磁盘文件），不可逆。"""
    db = load_db()
    to_remove = [s for s in db["sessions"] if s.get("couple_id") == couple_id]
    for s in to_remove:
        _delete_session_files(s)
    db["sessions"] = [s for s in db["sessions"] if s.get("couple_id") != couple_id]
    for c in db["couples"]:
        if c["couple_id"] == couple_id:
            c["couple_status"] = "dissolved"
    for u in db["users"]:
        if u.get("couple_id") == couple_id:
            u["couple_id"] = None
    save_db(db)


# ── 解绑协议 ──────────────────────────────────────────────────────────────

def initiate_uncouple(user_id: str) -> None:
    """单方发起分手，进入 90 天冻结期。"""
    couple = get_couple_for_user(user_id)
    if not couple or couple["couple_status"] != "active":
        return
    freeze_ends = datetime.now() + timedelta(days=90)
    _update_couple(couple["couple_id"], {
        "couple_status":         "frozen",
        "uncouple_initiated_by": user_id,
        "uncouple_initiated_at": _now_str(),
        "freeze_ends_at":        freeze_ends.strftime("%Y-%m-%d %H:%M:%S"),
    })


def agree_uncouple(user_id: str) -> None:
    """对方同意解绑，立即销毁全部数据。"""
    couple = get_couple_for_user(user_id)
    if not couple:
        return
    _update_couple(couple["couple_id"], {"both_agreed_uncouple": True})
    destroy_couple_data(couple["couple_id"])
