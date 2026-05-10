"""User repository backed by the local JSON database."""

from __future__ import annotations

import uuid

import bcrypt

from backend.domain.models import User
from backend.infrastructure.database.db import load_db, now_str, save_db


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_user(username: str, password: str) -> User:
    db = load_db()
    user = User(
        user_id="usr_" + uuid.uuid4().hex[:8],
        username=username,
        password_hash=_hash_password(password),
        couple_id=None,
        joined_at=now_str(),
    )
    db["users"].append(user.to_dict())
    save_db(db)
    return user


def get_user_by_username(username: str) -> User | None:
    db = load_db()
    for raw_user in db["users"]:
        if raw_user["username"] == username:
            return User.from_dict(raw_user)
    return None


def get_user_by_id(user_id: str) -> User | None:
    db = load_db()
    for raw_user in db["users"]:
        if raw_user["user_id"] == user_id:
            return User.from_dict(raw_user)
    return None


def verify_password(user: User, password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8"))


def update_user(user_id: str, fields: dict) -> User | None:
    db = load_db()
    updated = None
    for raw_user in db["users"]:
        if raw_user["user_id"] == user_id:
            raw_user.update(fields)
            updated = User.from_dict(raw_user)
            break
    save_db(db)
    return updated
