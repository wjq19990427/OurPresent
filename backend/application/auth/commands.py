"""User registration and login use cases."""

from __future__ import annotations

from backend.application.auth.errors import AuthError
from backend.domain.models import User
from backend.infrastructure.database.users_repo import (
    create_user,
    get_user_by_username,
    verify_password,
)


def register(username: str, password: str) -> User:
    username = username.strip()
    if not (2 <= len(username) <= 20):
        raise AuthError("用户名须在 2-20 个字符之间")
    if len(password) < 6:
        raise AuthError("密码至少需要 6 位")
    if get_user_by_username(username):
        raise AuthError(f"用户名「{username}」已被注册")
    return create_user(username, password)


def login(username: str, password: str) -> User:
    username = username.strip()
    user = get_user_by_username(username)
    if not user:
        raise AuthError("用户名不存在")
    if not verify_password(user, password):
        raise AuthError("密码错误")
    return user
