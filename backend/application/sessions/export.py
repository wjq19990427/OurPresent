"""Session export workflows."""

from __future__ import annotations

from pathlib import Path

from backend.infrastructure.database.sessions_repo import list_sessions_for_user


def collect_export_files(user_id: str) -> list[Path]:
    paths: list[Path] = []
    for session in list_sessions_for_user(user_id):
        for file_record in session.files:
            path = Path(file_record.get("path", ""))
            if path.exists():
                paths.append(path)
    return paths
