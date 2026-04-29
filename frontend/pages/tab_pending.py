"""
Tab 2 — 🖼️ 灵感墙（待处理）
"""

from __future__ import annotations

import streamlit as st

from frontend.components import _uid, _is_frozen, render_card, render_detail


def render_pending_tab(db: dict) -> None:
    sessions = sorted(
        [
            s for s in db["sessions"]
            if s.get("status") == "pending" and s.get("user_id") == _uid()
        ],
        key=lambda s: s.get("upload_time", ""),
        reverse=True,
    )
    if not sessions:
        st.info("暂无待处理记录。")
        return

    selected_id = st.session_state.get("pending_selected")

    cols = st.columns(3)
    for i, s in enumerate(sessions):
        render_card(cols[i % 3], s, "pending_selected")

    if selected_id:
        session = next((s for s in sessions if s["session_id"] == selected_id), None)
        if session:
            st.divider()
            st.markdown(f"### 详情 — {selected_id}")
            render_detail(session, mode="pending", read_only=_is_frozen())
        else:
            st.session_state["pending_selected"] = None
