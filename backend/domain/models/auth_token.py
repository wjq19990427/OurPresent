"""Authentication token domain model."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class AuthToken:
    token: str
    user_id: str
    expires_at: str

    @classmethod
    def from_dict(cls, data: dict) -> "AuthToken":
        return cls(
            token=data["token"],
            user_id=data["user_id"],
            expires_at=data["expires_at"],
        )

    def to_dict(self) -> dict:
        return asdict(self)
