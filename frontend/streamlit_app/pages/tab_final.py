"""Tab 3 - archived sessions."""

from __future__ import annotations

import streamlit as st

from backend.infrastructure.database.sessions_repo import list_sessions_for_user
from frontend.streamlit_app.components import _is_frozen, _uid, render_card, render_detail


def render_archived_tab(db: dict) -> None:
    sessions = sorted(
        [
            session
            for session in list_sessions_for_user(_uid())
            if session.status == "final"
        ],
        key=lambda session: session.upload_time,
        reverse=True,
    )
    if not sessions:
        st.info("暂无已归档记录。")
        return

    selected_id = st.session_state.get("archived_selected")

    cols = st.columns(3)
    for index, session in enumerate(sessions):
        render_card(cols[index % 3], session, "archived_selected")

    if selected_id:
        session = next((item for item in sessions if item.session_id == selected_id), None)
        if session:
            st.divider()
            st.markdown(f"### 详情 — {selected_id}")
            render_detail(session, mode="final", read_only=_is_frozen())
        else:
            st.session_state["archived_selected"] = None
