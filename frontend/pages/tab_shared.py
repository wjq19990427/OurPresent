"""
Tab 4 — 💌 情侣空间（对方共享给我的记录）
"""

from __future__ import annotations

import streamlit as st

from backend.db_manager import get_user_by_id
from backend.auth_manager import can_view_session
from frontend.components import _uid, _couple, _partner_id, render_card, render_detail


def render_shared_tab(db: dict) -> None:
    couple = _couple()
    if not couple or couple.get("couple_status") != "active":
        st.info("你还没有绑定伴侣，请在「账户」页进行绑定。")
        return

    partner_id = _partner_id()
    shared_sessions = sorted(
        [
            s for s in db["sessions"]
            if s.get("user_id") == partner_id
            and s.get("visibility") == "shared"
            and can_view_session(s, _uid())
        ],
        key=lambda s: s.get("shared_at", ""),
        reverse=True,
    )

    if not shared_sessions:
        st.info("伴侣暂时没有共享给你的记录。")
        return

    selected_id = st.session_state.get("shared_selected")

    cols = st.columns(3)
    for i, s in enumerate(shared_sessions):
        render_card(cols[i % 3], s, "shared_selected")

    if selected_id:
        session = next((s for s in shared_sessions if s["session_id"] == selected_id), None)
        if session:
            st.divider()
            partner      = get_user_by_id(partner_id)
            partner_name = partner["username"] if partner else partner_id
            st.markdown(f"### {partner_name} 的记录 — {selected_id}")
            render_detail(session, mode="final", read_only=True)
        else:
            st.session_state["shared_selected"] = None
