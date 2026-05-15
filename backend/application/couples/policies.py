"""Pure business rules for couple workflows."""

from __future__ import annotations

from backend.application.couples.errors import CoupleError
from backend.infrastructure.database.couples_repo import get_couple_for_user
from backend.infrastructure.database.users_repo import get_user_by_id


def ensure_can_send_bind_request(from_user_id: str, to_user_id: str) -> None:
    if from_user_id == to_user_id:
        raise CoupleError("不能向自己发送绑定请求")

    to_user = get_user_by_id(to_user_id)
    if not to_user:
        raise CoupleError(f"找不到 ID 为 {to_user_id} 的用户")

    for user_id in (from_user_id, to_user_id):
        existing = get_couple_for_user(user_id)
        if not existing:
            continue
        status = existing.couple_status
        if status == "active":
            raise CoupleError("对方已有绑定关系，无法发送请求")
        if status == "frozen":
            raise CoupleError("对方当前处于冻结期，无法发送请求")
        if status == "pending_bind":
            raise CoupleError("已存在待确认的绑定请求，请等待对方回应")


def ensure_can_start_uncouple(user_id: str) -> None:
    couple = get_couple_for_user(user_id)
    if not couple:
        raise CoupleError("当前没有绑定关系")
    if couple.couple_status == "frozen":
        raise CoupleError("解绑程序已在进行中")


def ensure_can_confirm_uncouple(user_id: str) -> None:
    if not get_couple_for_user(user_id):
        raise CoupleError("当前没有绑定关系")


def ensure_can_request_cancel_uncouple(user_id: str) -> None:
    couple = get_couple_for_user(user_id)
    if not couple or couple.couple_status != "frozen":
        raise CoupleError("当前不在冻结期")
    if couple.cancel_uncouple_requested_by:
        raise CoupleError("已有待回应的撤回请求")


def ensure_can_confirm_cancel_uncouple(user_id: str) -> None:
    couple = get_couple_for_user(user_id)
    if not couple or couple.couple_status != "frozen":
        raise CoupleError("当前不在冻结期")
    if not couple.cancel_uncouple_requested_by:
        raise CoupleError("当前没有待回应的撤回请求")
    if couple.cancel_uncouple_requested_by == user_id:
        raise CoupleError("请等待对方回应这次撤回请求")


def ensure_can_reject_cancel_uncouple(user_id: str) -> None:
    ensure_can_confirm_cancel_uncouple(user_id)


def ensure_can_withdraw_cancel_request(user_id: str) -> None:
    couple = get_couple_for_user(user_id)
    if not couple or couple.couple_status != "frozen":
        raise CoupleError("当前不在冻结期")
    if not couple.cancel_uncouple_requested_by:
        raise CoupleError("当前没有可撤回的请求")
    if couple.cancel_uncouple_requested_by != user_id:
        raise CoupleError("只有发起请求的人可以撤回")
