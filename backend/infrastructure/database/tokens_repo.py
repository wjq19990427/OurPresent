"""Auth token repository backed by the local JSON database."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from backend.config.settings import TOKEN_EXPIRE_HOURS
from backend.domain.models import AuthToken
from backend.infrastructure.database.db import load_db, parse_dt, save_db


def create_auth_token(user_id: str) -> AuthToken:
    db = load_db()
    token = AuthToken(
        token=uuid.uuid4().hex,
        user_id=user_id,
        expires_at=(datetime.now() + timedelta(hours=TOKEN_EXPIRE_HOURS)).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    )
    db.setdefault("auth_tokens", []).append(token.to_dict())
    save_db(db)
    return token


def get_valid_auth_token(token: str) -> AuthToken | None:
    if not token:
        return None
    db = load_db()
    now = datetime.now()
    for raw_token in db.get("auth_tokens", []):
        if raw_token["token"] != token:
            continue
        expires = parse_dt(raw_token.get("expires_at", ""))
        if expires and expires > now:
            return AuthToken.from_dict(raw_token)
        return None
    return None


def revoke_auth_token(token: str) -> None:
    if not token:
        return
    db = load_db()
    db["auth_tokens"] = [
        raw_token for raw_token in db.get("auth_tokens", []) if raw_token["token"] != token
    ]
    save_db(db)
