"""User domain model."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class User:
    user_id: str
    username: str
    password_hash: str
    couple_id: str | None
    joined_at: str
    weekly_report_enabled: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            password_hash=data["password_hash"],
            couple_id=data.get("couple_id"),
            joined_at=data["joined_at"],
            weekly_report_enabled=bool(data.get("weekly_report_enabled", False)),
        )

    def to_dict(self) -> dict:
        return asdict(self)
