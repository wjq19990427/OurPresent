"""Farewell page shown after a relationship is dissolved."""

from __future__ import annotations

import streamlit as st


def _farewell_copy(reason: str) -> tuple[str, str]:
    if reason == "freeze_expired":
        return (
            "90 天已经走完，这段关系也在这里轻轻放下了。",
            "共同数据已经按约定被永久销毁。接下来，慢慢回到各自的生活里就好。",
        )
    return (
        "你们已经在这里停下，这段共同留下的内容也随之放下了。",
        "共同数据已经被永久销毁，之后无法恢复。",
    )


def render_farewell_page() -> None:
    reason = (st.session_state.get("farewell_state") or {}).get("reason", "destroy_now")
    title, body = _farewell_copy(reason)

    st.title("💑 OurPresent")
    st.caption("有些故事走到这里，也可以安静地收好。")
    st.divider()

    with st.container(border=True):
        st.markdown(f"### {title}")
        st.write(body)
        st.caption("这个页面会先留在这里，等你准备好再回到首页。")
        if st.button("返回首页", width="stretch", type="primary"):
            st.session_state["farewell_state"] = None
            if "farewell" in st.query_params:
                del st.query_params["farewell"]
            st.rerun()
