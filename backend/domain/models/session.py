"""Session domain model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    user_id: str
    couple_id: str | None
    status: str
    visibility: str
    unlock_requested_at: str | None
    unlock_at: str | None
    shared_at: str | None
    upload_time: str
    archive_time: str
    is_complete: bool
    edit_history: list[dict] = field(default_factory=list)
    files: list[dict] = field(default_factory=list)
    source_type: str = "file"
    content_time: str = ""
    description: str = ""
    feeling: str = ""
    reason: str = ""
    comments: list[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionRecord":
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            couple_id=data.get("couple_id"),
            status=data.get("status", "pending"),
            visibility=data.get("visibility", "private"),
            unlock_requested_at=data.get("unlock_requested_at"),
            unlock_at=data.get("unlock_at") or None,
            shared_at=data.get("shared_at"),
            upload_time=data.get("upload_time", ""),
            archive_time=data.get("archive_time", ""),
            is_complete=bool(data.get("is_complete", False)),
            edit_history=list(data.get("edit_history", [])),
            files=list(data.get("files", [])),
            source_type=data.get("source_type", "file"),
            content_time=data.get("content_time", ""),
            description=data.get("description", ""),
            feeling=data.get("feeling", ""),
            reason=data.get("reason", ""),
            comments=list(data.get("comments", [])),
        )

    def to_dict(self) -> dict:
        return asdict(self)
