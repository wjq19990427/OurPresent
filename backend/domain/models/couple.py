"""Couple relationship domain model."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class Couple:
    couple_id: str
    user_a: str
    user_b: str
    created_at: str
    couple_status: str
    uncouple_initiated_by: str | None
    uncouple_initiated_at: str | None
    both_agreed_uncouple: bool
    freeze_ends_at: str | None

    @classmethod
    def from_dict(cls, data: dict) -> "Couple":
        return cls(
            couple_id=data["couple_id"],
            user_a=data["user_a"],
            user_b=data["user_b"],
            created_at=data["created_at"],
            couple_status=data["couple_status"],
            uncouple_initiated_by=data.get("uncouple_initiated_by"),
            uncouple_initiated_at=data.get("uncouple_initiated_at"),
            both_agreed_uncouple=bool(data.get("both_agreed_uncouple", False)),
            freeze_ends_at=data.get("freeze_ends_at"),
        )

    def to_dict(self) -> dict:
        return asdict(self)
