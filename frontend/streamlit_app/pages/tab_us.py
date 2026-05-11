"""Us tab - shared couple timeline."""

from __future__ import annotations

import streamlit as st

from backend.application.sessions import can_view_session
from backend.infrastructure.database.sessions_repo import list_sessions_for_couple
from backend.infrastructure.database.users_repo import get_user_by_id
from frontend.streamlit_app.components import _couple, _uid, render_card, render_detail


def _username(user_id: str) -> str:
    user = get_user_by_id(user_id)
    return user.username if user else user_id


def render_us_tab(db: dict) -> None:
    couple = _couple()
    if not couple or couple.couple_status != "active":
        st.info("先去「设置」里绑定伴侣。")
        return

    sessions = sorted(
        [
            session
            for session in list_sessions_for_couple(couple.couple_id)
            if session.visibility == "shared" and can_view_session(session, _uid())
        ],
        key=lambda session: session.shared_at or "",
        reverse=True,
    )

    if not sessions:
        st.info("还没有共享的记录，去「我的」写一条吧。")
        return

    selected_id = st.session_state.get("us_selected")

    for session in sessions:
        is_mine = session.user_id == _uid()
        left, right = st.columns([1, 2] if is_mine else [2, 1], gap="large")
        target_col = right if is_mine else left
        render_card(
            target_col,
            session,
            "us_selected",
            author_name=_username(session.user_id),
        )

    if selected_id:
        session = next((item for item in sessions if item.session_id == selected_id), None)
        if session:
            st.divider()
            st.markdown(f"### {_username(session.user_id)} 的记录 — {selected_id}")
            render_detail(
                session,
                mode="final",
                read_only=True,
                selected_state_key="us_selected",
            )
        else:
            st.session_state["us_selected"] = None
