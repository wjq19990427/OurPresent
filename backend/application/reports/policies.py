"""Service activation policies for relationship reports."""

from __future__ import annotations

from typing import Literal

from backend.infrastructure.database.couples_repo import get_couple_by_id, get_couple_for_user
from backend.infrastructure.database.users_repo import get_user_by_id

PartnerEnabledStatus = Literal["both", "only_self", "only_partner", "neither"]


def _partner_id_for(couple, user_id: str) -> str | None:
    if not couple or couple.couple_status != "active":
        return None
    if couple.user_a == user_id:
        return couple.user_b
    if couple.user_b == user_id:
        return couple.user_a
    return None


def service_active_for_couple(couple_id: str) -> bool:
    couple = get_couple_by_id(couple_id)
    if not couple or couple.couple_status != "active":
        return False

    user_a = get_user_by_id(couple.user_a)
    user_b = get_user_by_id(couple.user_b)
    if not user_a or not user_b:
        return False

    return bool(user_a.weekly_report_enabled and user_b.weekly_report_enabled)


def partner_enabled_status(user_id: str) -> PartnerEnabledStatus:
    user = get_user_by_id(user_id)
    couple = get_couple_for_user(user_id)
    partner_id = _partner_id_for(couple, user_id)
    partner = get_user_by_id(partner_id) if partner_id else None

    self_enabled = bool(user.weekly_report_enabled) if user else False
    partner_enabled = bool(partner.weekly_report_enabled) if partner else False

    if self_enabled and partner_enabled:
        return "both"
    if self_enabled:
        return "only_self"
    if partner_enabled:
        return "only_partner"
    return "neither"
