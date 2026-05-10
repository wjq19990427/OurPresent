from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from backend.application.auth import (
    AuthError,
    create_auth_token,
    login,
    register,
    revoke_auth_token,
    validate_auth_token,
)
from backend.infrastructure.database import db as db_module
from backend.infrastructure.database.tokens_repo import get_valid_auth_token
from backend.infrastructure.database.users_repo import get_user_by_username, verify_password


def test_register_and_login_success() -> None:
    user = register("  alice  ", "secret123")

    assert user.username == "alice"
    assert get_user_by_username("alice") is not None
    assert not _is_sha256_hex(user.password_hash)
    assert login(" alice ", "secret123").user_id == user.user_id


@pytest.mark.parametrize(
    ("username", "password", "message"),
    [
        ("a", "secret123", "用户名须在 2-20 个字符之间"),
        ("alice", "12345", "密码至少需要 6 位"),
    ],
)
def test_register_validation_errors(username: str, password: str, message: str) -> None:
    with pytest.raises(AuthError, match=message):
        register(username, password)


def test_register_rejects_duplicate_username() -> None:
    register("alice", "secret123")

    with pytest.raises(AuthError, match="已被注册"):
        register("alice", "another123")


def test_login_errors() -> None:
    with pytest.raises(AuthError, match="用户名不存在"):
        login("missing", "secret123")

    register("alice", "secret123")
    with pytest.raises(AuthError, match="密码错误"):
        login("alice", "wrongpass")


def test_password_hash_uses_bcrypt_with_independent_salts() -> None:
    user = register("alice", "secret123")
    other = register("bob", "secret123")

    assert user.password_hash != other.password_hash
    assert user.password_hash.startswith("$2")
    assert other.password_hash.startswith("$2")
    assert not _is_sha256_hex(user.password_hash)
    assert not _is_sha256_hex(other.password_hash)
    assert verify_password(user, "secret123")
    assert not verify_password(user, "wrongpass")


def test_auth_token_lifecycle() -> None:
    user = register("alice", "secret123")

    token = create_auth_token(user.user_id)
    validated = validate_auth_token(token)

    assert validated is not None
    assert validated.user_id == user.user_id
    assert get_valid_auth_token(token) is not None

    revoke_auth_token(token)

    assert validate_auth_token(token) is None
    assert get_valid_auth_token(token) is None


def test_expired_token_is_not_valid() -> None:
    user = register("alice", "secret123")
    expired = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    db = db_module.load_db()
    db["auth_tokens"].append({"token": "expired", "user_id": user.user_id, "expires_at": expired})
    db_module.save_db(db)

    assert get_valid_auth_token("expired") is None
    assert validate_auth_token("expired") is None


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)
