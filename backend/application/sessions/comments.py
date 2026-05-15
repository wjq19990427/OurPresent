"""Session comment workflows."""

from __future__ import annotations

from datetime import datetime

from backend.application.sessions.markdown import write_session_markdown
from backend.infrastructure.database.sessions_repo import get_session_by_id, replace_session


def add_comment(session_id: str, author_id: str, text: str) -> None:
    session = get_session_by_id(session_id)
    if not session:
        return
    now = datetime.now()
    session.comments.append(
        {
            "id": now.strftime("%Y%m%d_%H%M%S_") + str(now.microsecond),
            "author": author_id,
            "text": text,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    replace_session(session)
    if session.status == "final":
        write_session_markdown(session)


def delete_comment(session_id: str, comment_id: str, author_id: str) -> None:
    session = get_session_by_id(session_id)
    if not session:
        return
    target = next((comment for comment in session.comments if comment["id"] == comment_id), None)
    if not target:
        return
    if target.get("author") != author_id:
        raise ValueError("cannot delete another user's comment")
    session.comments = [comment for comment in session.comments if comment["id"] != comment_id]
    replace_session(session)
    if session.status == "final":
        write_session_markdown(session)
