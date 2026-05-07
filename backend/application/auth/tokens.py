"""Authentication token application services."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.infrastructure.database.tokens_repo import (
    create_auth_token as _create_auth_token,
)
from backend.infrastructure.database.tokens_repo import (
    get_valid_auth_token,
)
from backend.infrastructure.database.tokens_repo import (
    revoke_auth_token as _revoke_auth_token,
)
from backend.infrastructure.database.users_repo import get_user_by_id

if TYPE_CHECKING:
    from backend.domain.models import User


def create_auth_token(user_id: str) -> str:
    return _create_auth_token(user_id).token


def validate_auth_token(token: str) -> User | None:
    auth_token = get_valid_auth_token(token)
    if not auth_token:
        return None
    return get_user_by_id(auth_token.user_id)


def revoke_auth_token(token: str) -> None:
    _revoke_auth_token(token)
