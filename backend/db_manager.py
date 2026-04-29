"""
数据层：JSON 数据库读写、User/Couple CRUD、登录 Token 管理。
不依赖 Streamlit，可独立作为后端数据访问层复用。
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.config import (
    DATA_DIR, DB_PATH, ASSETS_DIR, PENDING_DIR, FINAL_DIR,
    TOKEN_EXPIRE_HOURS,
)

# ── 工具函数 ──────────────────────────────────────────────────────────────

def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_dt(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _hash_password(password: str) -> str:
    salt = "projects_salt_v1"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


# ── 数据库读写 ────────────────────────────────────────────────────────────

_EMPTY_DB: dict = {"users": [], "couples": [], "sessions": [], "auth_tokens": []}


def load_db() -> dict:
    if not DB_PATH.exists():
        return {k: list(v) for k, v in _EMPTY_DB.items()}
    try:
        raw = json.loads(DB_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return {"users": [], "couples": [], "sessions": raw, "auth_tokens": []}
        if "auth_tokens" not in raw:
            raw["auth_tokens"] = []
        return raw
    except (json.JSONDecodeError, OSError):
        return {k: list(v) for k, v in _EMPTY_DB.items()}


def save_db(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)


# ── 用户 CRUD ─────────────────────────────────────────────────────────────

def create_user(username: str, password: str) -> dict:
    """创建新用户，返回 user 记录。调用方需确保 username 唯一。"""
    db = load_db()
    user_id = "usr_" + uuid.uuid4().hex[:8]
    user = {
        "user_id":       user_id,
        "username":      username,
        "password_hash": _hash_password(password),
        "couple_id":     None,
        "joined_at":     _now_str(),
    }
    db["users"].append(user)
    save_db(db)
    return user


def get_user_by_username(username: str) -> Optional[dict]:
    db = load_db()
    for u in db["users"]:
        if u["username"] == username:
            return u
    return None


def get_user_by_id(user_id: str) -> Optional[dict]:
    db = load_db()
    for u in db["users"]:
        if u["user_id"] == user_id:
            return u
    return None


def verify_password(user: dict, password: str) -> bool:
    return user["password_hash"] == _hash_password(password)


def _update_user(user_id: str, fields: dict) -> None:
    db = load_db()
    for u in db["users"]:
        if u["user_id"] == user_id:
            u.update(fields)
            break
    save_db(db)


# ── 情侣绑定 CRUD ─────────────────────────────────────────────────────────

def send_couple_request(from_user_id: str, to_user_id: str) -> dict:
    """发起绑定请求，返回新建的 couple 记录。"""
    db = load_db()
    couple_id = "cp_" + uuid.uuid4().hex[:8]
    couple = {
        "couple_id":             couple_id,
        "user_a":                from_user_id,
        "user_b":                to_user_id,
        "created_at":            _now_str(),
        "couple_status":         "pending_bind",
        "uncouple_initiated_by": None,
        "uncouple_initiated_at": None,
        "both_agreed_uncouple":  False,
        "freeze_ends_at":        None,
    }
    db["couples"].append(couple)
    save_db(db)
    return couple


def get_couple_by_id(couple_id: str) -> Optional[dict]:
    db = load_db()
    for c in db["couples"]:
        if c["couple_id"] == couple_id:
            return c
    return None


def get_couple_for_user(user_id: str) -> Optional[dict]:
    """返回该用户当前有效的 couple 记录（不含已解散）。"""
    db = load_db()
    for c in db["couples"]:
        if c["couple_status"] in ("pending_bind", "active", "frozen"):
            if user_id in (c["user_a"], c["user_b"]):
                return c
    return None


def get_pending_requests_for_user(user_id: str) -> list[dict]:
    """返回目标为该用户且状态为 pending_bind 的绑定请求列表。"""
    db = load_db()
    return [
        c for c in db["couples"]
        if c["couple_status"] == "pending_bind" and c["user_b"] == user_id
    ]


def accept_couple_request(couple_id: str) -> None:
    """接受绑定，双方 user 的 couple_id 更新。"""
    db = load_db()
    couple = None
    for c in db["couples"]:
        if c["couple_id"] == couple_id:
            c["couple_status"] = "active"
            couple = c
            break
    if couple:
        for u in db["users"]:
            if u["user_id"] in (couple["user_a"], couple["user_b"]):
                u["couple_id"] = couple_id
    save_db(db)


def reject_couple_request(couple_id: str) -> None:
    db = load_db()
    db["couples"] = [c for c in db["couples"] if c["couple_id"] != couple_id]
    save_db(db)


def _update_couple(couple_id: str, fields: dict) -> None:
    db = load_db()
    for c in db["couples"]:
        if c["couple_id"] == couple_id:
            c.update(fields)
            break
    save_db(db)


# ── 登录 Token ────────────────────────────────────────────────────────────

def create_auth_token(user_id: str) -> str:
    """创建登录 token，写入 DB，返回 token 字符串。"""
    db = load_db()
    token = uuid.uuid4().hex
    expires_at = datetime.now() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    db.setdefault("auth_tokens", []).append({
        "token":      token,
        "user_id":    user_id,
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_db(db)
    return token


def validate_auth_token(token: str) -> Optional[dict]:
    """校验 token，有效时返回对应 user 记录，无效/过期返回 None。"""
    if not token:
        return None
    db = load_db()
    now = datetime.now()
    for t in db.get("auth_tokens", []):
        if t["token"] == token:
            expires = _parse_dt(t.get("expires_at", ""))
            if expires and expires > now:
                return get_user_by_id(t["user_id"])
            break
    return None


def revoke_auth_token(token: str) -> None:
    """使 token 失效（退出登录时调用）。"""
    if not token:
        return
    db = load_db()
    db["auth_tokens"] = [t for t in db.get("auth_tokens", []) if t["token"] != token]
    save_db(db)
