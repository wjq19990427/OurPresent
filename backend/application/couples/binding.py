"""Bind request workflows."""

from __future__ import annotations

from backend.application.couples.policies import ensure_can_send_bind_request
from backend.domain.models import Couple
from backend.infrastructure.database.couples_repo import (
    accept_couple_request,
    create_couple_request,
    reject_couple_request,
)


def send_bind_request(from_user_id: str, to_user_id: str) -> Couple:
    ensure_can_send_bind_request(from_user_id, to_user_id)
    return create_couple_request(from_user_id, to_user_id)


def accept_bind(couple_id: str) -> None:
    accept_couple_request(couple_id)


def reject_bind(couple_id: str) -> None:
    reject_couple_request(couple_id)
