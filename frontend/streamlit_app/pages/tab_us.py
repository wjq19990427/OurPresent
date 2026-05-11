"""Us tab - shared couple timeline."""

from __future__ import annotations

import streamlit as st

from backend.application.reports import (
    generate_weekly_report,
    list_reports,
    partner_enabled_status,
    service_active_for_couple,
)
from backend.application.sessions import can_view_session
from backend.infrastructure.database.sessions_repo import list_sessions_for_couple
from backend.infrastructure.database.users_repo import get_user_by_id
from frontend.streamlit_app.components import (
    _couple,
    _uid,
    render_card,
    render_detail,
    render_weekly_report,
)


def _username(user_id: str) -> str:
    user = get_user_by_id(user_id)
    return user.username if user else user_id


def _settings_hint_button(key: str) -> None:
    if st.button("去「设置」开启", key=key, use_container_width=True):
        st.info("入口在上方「⚙️ 设置」tab 的「情感周报服务」里。")


def _render_weekly_report_panel(couple) -> None:
    # TASK-9 临时按钮，cron 稳定后另开任务删除
    active = service_active_for_couple(couple.couple_id)
    reports = list_reports(couple.couple_id)
    latest_report = reports[0] if reports else None
    status = partner_enabled_status(_uid())

    with st.expander("📊 周报", expanded=False):
        if couple.couple_status == "frozen":
            st.info("冻结期内不会生成新的周报，已经生成的历史仍可查看。")
            latest_visible = next(
                (report for report in reports if report.status != "failed"),
                None,
            )
            if latest_visible:
                render_weekly_report(latest_visible)
            else:
                st.caption("还没有可查看的历史周报。")
            return

        if active:
            # TASK-9 临时按钮，cron 稳定后另开任务删除
            if st.button("🧪 立即生成周报（测试）", use_container_width=True):
                generate_weekly_report(couple.couple_id)
                st.rerun()
            st.caption("（临时入口，cron 稳定后将由架构师删除）")

        if status == "both":
            if not latest_report:
                st.info("邀请你写下第一周的共享记录。")
            elif latest_report.status == "failed":
                st.info("上一次生成遇到了一些波折，会在下次自动重试。")
            else:
                render_weekly_report(latest_report)
        elif status == "only_partner":
            st.info("对方已开启周报，要不要一起？")
            _settings_hint_button("weekly_only_partner_settings")
        elif status == "only_self":
            st.info("⌛ 等待对方一同开启。对方可以在「设置」里的情感周报服务中打开开关。")
        else:
            st.info("一起开启情感周报，每周看到我们的足迹。")
            _settings_hint_button("weekly_neither_settings")


def render_us_tab(db: dict) -> None:
    couple = _couple()
    if not couple:
        st.info("先去「设置」里绑定伴侣。")
        return
    if couple.couple_status == "pending_bind":
        st.info("绑定确认后，这里会出现你们共享的记录。")
        return

    _render_weekly_report_panel(couple)
    st.divider()

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
