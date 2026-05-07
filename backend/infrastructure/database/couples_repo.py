"""Couple repository backed by the local JSON database."""

from __future__ import annotations

import uuid

from backend.domain.models import Couple
from backend.infrastructure.database.db import load_db, now_str, save_db


def create_couple_request(from_user_id: str, to_user_id: str) -> Couple:
    db = load_db()
    couple = Couple(
        couple_id="cp_" + uuid.uuid4().hex[:8],
        user_a=from_user_id,
        user_b=to_user_id,
        created_at=now_str(),
        couple_status="pending_bind",
        uncouple_initiated_by=None,
        uncouple_initiated_at=None,
        both_agreed_uncouple=False,
        freeze_ends_at=None,
    )
    db["couples"].append(couple.to_dict())
    save_db(db)
    return couple


def get_couple_by_id(couple_id: str) -> Couple | None:
    db = load_db()
    for raw_couple in db["couples"]:
        if raw_couple["couple_id"] == couple_id:
            return Couple.from_dict(raw_couple)
    return None


def get_couple_for_user(user_id: str) -> Couple | None:
    db = load_db()
    for raw_couple in db["couples"]:
        if raw_couple["couple_status"] in ("pending_bind", "active", "frozen"):
            if user_id in (raw_couple["user_a"], raw_couple["user_b"]):
                return Couple.from_dict(raw_couple)
    return None


def get_pending_requests_for_user(user_id: str) -> list[Couple]:
    db = load_db()
    return [
        Couple.from_dict(raw_couple)
        for raw_couple in db["couples"]
        if raw_couple["couple_status"] == "pending_bind" and raw_couple["user_b"] == user_id
    ]


def accept_couple_request(couple_id: str) -> Couple | None:
    db = load_db()
    accepted = None
    for raw_couple in db["couples"]:
        if raw_couple["couple_id"] == couple_id:
            raw_couple["couple_status"] = "active"
            accepted = Couple.from_dict(raw_couple)
            break
    if accepted:
        for raw_user in db["users"]:
            if raw_user["user_id"] in (accepted.user_a, accepted.user_b):
                raw_user["couple_id"] = couple_id
    save_db(db)
    return accepted


def reject_couple_request(couple_id: str) -> None:
    db = load_db()
    db["couples"] = [
        raw_couple for raw_couple in db["couples"] if raw_couple["couple_id"] != couple_id
    ]
    save_db(db)


def update_couple(couple_id: str, fields: dict) -> Couple | None:
    db = load_db()
    updated = None
    for raw_couple in db["couples"]:
        if raw_couple["couple_id"] == couple_id:
            raw_couple.update(fields)
            updated = Couple.from_dict(raw_couple)
            break
    save_db(db)
    return updated
