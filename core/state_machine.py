"""
状态机推进：时间锁（pending_unlock→shared）与冻结期到期销毁。
UI 层每次加载时调用 load_db_with_tick()，不直接调用 load_db()。
"""

from __future__ import annotations

from datetime import datetime

from backend.db_manager import load_db, save_db, _parse_dt, _now_str
from backend.session_manager import destroy_couple_data


def tick(db: dict) -> bool:
    """
    在已加载的 db 对象上原地推进两类状态，有变化时返回 True。
    1. 时间锁：pending_unlock 且 upload_time 距今 ≥ 90 天 → shared
    2. 冻结期到期：frozen 且 freeze_ends_at ≤ now → destroy_couple_data
    3. 清理过期 auth_tokens
    """
    now = datetime.now()
    changed = False

    # 时间锁推进
    for s in db["sessions"]:
        if s.get("visibility") == "pending_unlock":
            upload_dt = _parse_dt(s.get("upload_time", ""))
            if upload_dt and (now - upload_dt).days >= 90:
                s["visibility"] = "shared"
                s["shared_at"]  = _now_str()
                changed = True

    # 冻结期到期销毁
    for c in db["couples"]:
        if c.get("couple_status") == "frozen" and c.get("freeze_ends_at"):
            ends = _parse_dt(c["freeze_ends_at"])
            if ends and now >= ends:
                destroy_couple_data(c["couple_id"])
                changed = True

    # 过期 token 清理
    before = len(db.get("auth_tokens", []))
    db["auth_tokens"] = [
        t for t in db.get("auth_tokens", [])
        if _parse_dt(t.get("expires_at", "")) and _parse_dt(t["expires_at"]) > now
    ]
    if len(db["auth_tokens"]) != before:
        changed = True

    return changed


def load_db_with_tick() -> dict:
    """加载 DB 并推进状态机，UI 层应始终调用此函数。"""
    db = load_db()
    if tick(db):
        save_db(db)
        db = load_db()
    return db
