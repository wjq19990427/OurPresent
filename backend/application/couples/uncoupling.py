"""Uncoupling and frozen-state workflows."""

from __future__ import annotations

from datetime import datetime, timedelta

from backend.application.couples.policies import (
    ensure_can_confirm_cancel_uncouple,
    ensure_can_confirm_uncouple,
    ensure_can_reject_cancel_uncouple,
    ensure_can_request_cancel_uncouple,
    ensure_can_start_uncouple,
    ensure_can_withdraw_cancel_request,
)
from backend.application.sessions.destruction import destroy_couple_data
from backend.infrastructure.database.couples_repo import get_couple_for_user, update_couple
from backend.infrastructure.database.db import now_str


def start_uncouple(user_id: str) -> None:
    ensure_can_start_uncouple(user_id)
    couple = get_couple_for_user(user_id)
    if not couple or couple.couple_status != "active":
        return

    freeze_ends = datetime.now() + timedelta(days=90)
    update_couple(
        couple.couple_id,
        {
            "couple_status": "frozen",
            "uncouple_initiated_by": user_id,
            "uncouple_initiated_at": now_str(),
            "freeze_ends_at": freeze_ends.strftime("%Y-%m-%d %H:%M:%S"),
            "cancel_uncouple_requested_by": None,
            "cancel_uncouple_requested_at": None,
        },
    )


def confirm_uncouple(user_id: str) -> None:
    ensure_can_confirm_uncouple(user_id)
    couple = get_couple_for_user(user_id)
    if not couple:
        return
    update_couple(couple.couple_id, {"both_agreed_uncouple": True})
    destroy_couple_data(couple.couple_id)


def request_cancel_uncouple(user_id: str) -> None:
    ensure_can_request_cancel_uncouple(user_id)
    couple = get_couple_for_user(user_id)
    if not couple:
        return
    update_couple(
        couple.couple_id,
        {
            "cancel_uncouple_requested_by": user_id,
            "cancel_uncouple_requested_at": now_str(),
        },
    )


def confirm_cancel_uncouple(user_id: str) -> None:
    ensure_can_confirm_cancel_uncouple(user_id)
    couple = get_couple_for_user(user_id)
    if not couple:
        return
    update_couple(
        couple.couple_id,
        {
            "couple_status": "active",
            "uncouple_initiated_by": None,
            "uncouple_initiated_at": None,
            "both_agreed_uncouple": False,
            "freeze_ends_at": None,
            "cancel_uncouple_requested_by": None,
            "cancel_uncouple_requested_at": None,
        },
    )


def reject_cancel_uncouple(user_id: str) -> None:
    ensure_can_reject_cancel_uncouple(user_id)
    couple = get_couple_for_user(user_id)
    if not couple:
        return
    update_couple(
        couple.couple_id,
        {
            "cancel_uncouple_requested_by": None,
            "cancel_uncouple_requested_at": None,
        },
    )


def withdraw_cancel_request(user_id: str) -> None:
    ensure_can_withdraw_cancel_request(user_id)
    couple = get_couple_for_user(user_id)
    if not couple:
        return
    update_couple(
        couple.couple_id,
        {
            "cancel_uncouple_requested_by": None,
            "cancel_uncouple_requested_at": None,
        },
    )


def is_frozen(user_id: str) -> bool:
    couple = get_couple_for_user(user_id)
    return bool(couple and couple.couple_status == "frozen")
