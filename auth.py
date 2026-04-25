"""
OurPresent — 鉴权层
封装注册/登录/情侣绑定/解绑的业务逻辑，不直接操作 Streamlit session_state。
"""

from __future__ import annotations

from typing import Optional

import db as db_module


# ── 注册 / 登录 ───────────────────────────────────────────────────────────
class AuthError(Exception):
    pass


def register(username: str, password: str) -> dict:
    """
    注册新用户，返回 user 记录。
    username 限 2-20 字符；password 至少 6 字符。
    """
    username = username.strip()
    if not (2 <= len(username) <= 20):
        raise AuthError("用户名须在 2-20 个字符之间")
    if len(password) < 6:
        raise AuthError("密码至少需要 6 位")
    if db_module.get_user_by_username(username):
        raise AuthError(f"用户名「{username}」已被注册")
    return db_module.create_user(username, password)


def login(username: str, password: str) -> dict:
    """登录，返回 user 记录；失败抛 AuthError。"""
    username = username.strip()
    user = db_module.get_user_by_username(username)
    if not user:
        raise AuthError("用户名不存在")
    if not db_module.verify_password(user, password):
        raise AuthError("密码错误")
    return user


# ── 情侣绑定 ──────────────────────────────────────────────────────────────
class CoupleError(Exception):
    pass


def send_bind_request(from_user_id: str, to_user_id: str) -> dict:
    """
    向目标用户发送绑定请求，返回新建的 couple 记录。
    双方均不能已有活跃绑定关系。
    """
    if from_user_id == to_user_id:
        raise CoupleError("不能向自己发送绑定请求")

    to_user = db_module.get_user_by_id(to_user_id)
    if not to_user:
        raise CoupleError(f"找不到 ID 为 {to_user_id} 的用户")

    for uid in (from_user_id, to_user_id):
        existing = db_module.get_couple_for_user(uid)
        if existing:
            status = existing["couple_status"]
            if status == "active":
                raise CoupleError("对方已有绑定关系，无法发送请求")
            if status == "frozen":
                raise CoupleError("对方当前处于冻结期，无法发送请求")
            if status == "pending_bind":
                raise CoupleError("已存在待确认的绑定请求，请等待对方回应")

    return db_module.send_couple_request(from_user_id, to_user_id)


def accept_bind(couple_id: str) -> None:
    db_module.accept_couple_request(couple_id)


def reject_bind(couple_id: str) -> None:
    db_module.reject_couple_request(couple_id)


# ── 解绑协议 ──────────────────────────────────────────────────────────────
def start_uncouple(user_id: str) -> None:
    """单方发起分手，进入 90 天冻结期。"""
    couple = db_module.get_couple_for_user(user_id)
    if not couple:
        raise CoupleError("当前没有绑定关系")
    if couple["couple_status"] == "frozen":
        raise CoupleError("解绑程序已在进行中")
    db_module.initiate_uncouple(user_id)


def confirm_uncouple(user_id: str) -> None:
    """对方确认解绑，立即销毁全部数据。"""
    couple = db_module.get_couple_for_user(user_id)
    if not couple:
        raise CoupleError("当前没有绑定关系")
    db_module.agree_uncouple(user_id)


# ── 视图权限检查 ──────────────────────────────────────────────────────────
def can_view_session(session: dict, viewer_id: str) -> bool:
    """
    判断 viewer 是否有权查看该 session。
    规则：
    - 创建者始终可见（private / pending_unlock / shared 均可）
    - 情侣对方：仅 visibility == "shared" 时可见
    """
    if session.get("user_id") == viewer_id:
        return True
    # 对方查看
    viewer = db_module.get_user_by_id(viewer_id)
    if not viewer:
        return False
    if viewer.get("couple_id") != session.get("couple_id"):
        return False
    return session.get("visibility") == "shared"


def is_frozen(user_id: str) -> bool:
    """当前用户所在的情侣关系是否处于冻结期（只读状态）。"""
    couple = db_module.get_couple_for_user(user_id)
    return bool(couple and couple.get("couple_status") == "frozen")
