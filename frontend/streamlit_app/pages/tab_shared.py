"""Tab 4 - partner shared sessions."""

from __future__ import annotations

import streamlit as st

from backend.application.sessions import can_view_session
from backend.infrastructure.database.users_repo import get_user_by_id
from frontend.streamlit_app.components import _couple, _partner_id, _uid, render_card, render_detail


def render_shared_tab(db: dict) -> None:
    couple = _couple()
    if not couple or couple.couple_status != "active":
        st.info("你还没有绑定伴侣，请在「账户」页进行绑定。")
        return

    partner_id = _partner_id()
    shared_sessions = sorted(
        [
            session
            for session in db["sessions"]
            if session.get("user_id") == partner_id
            and session.get("visibility") == "shared"
            and can_view_session(session, _uid())
        ],
        key=lambda session: session.get("shared_at", ""),
        reverse=True,
    )

    if not shared_sessions:
        st.info("伴侣暂时没有共享给你的记录。")
        return

    selected_id = st.session_state.get("shared_selected")

    cols = st.columns(3)
    for index, session in enumerate(shared_sessions):
        render_card(cols[index % 3], session, "shared_selected")

    if selected_id:
        session = next(
            (item for item in shared_sessions if item["session_id"] == selected_id), None
        )
        if session:
            st.divider()
            partner = get_user_by_id(partner_id)
            partner_name = partner.username if partner else partner_id
            st.markdown(f"### {partner_name} 的记录 — {selected_id}")
            render_detail(session, mode="final", read_only=True)
        else:
            st.session_state["shared_selected"] = None
