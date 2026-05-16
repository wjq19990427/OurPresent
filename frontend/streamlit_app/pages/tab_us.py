"""Us tab - shared couple timeline."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from backend.application.reports import (
    generate_weekly_report,
    list_reports,
    partner_enabled_status,
    service_active_for_couple,
)
from backend.application.sessions import can_view_session
from backend.infrastructure.database.db import parse_dt
from backend.infrastructure.database.sessions_repo import list_sessions_for_couple
from backend.infrastructure.database.users_repo import get_user_by_id
from frontend.streamlit_app.components import (
    SETTINGS_BIND_SECTION_ID,
    SETTINGS_REPORT_SECTION_ID,
    _couple,
    _is_recently_shared,
    _uid,
    render_card,
    render_comments,
    render_tab_jump_button,
    render_weekly_report,
)


def _username(user_id: str) -> str:
    user = get_user_by_id(user_id)
    return user.username if user else user_id


def _settings_hint_button(key: str) -> None:
    render_tab_jump_button(
        "去「设置」开启",
        "⚙️ 设置",
        key=key,
        target_section_id=SETTINGS_REPORT_SECTION_ID,
    )


def _should_show_first_shared_moment(sessions) -> bool:
    shared_sessions = [session for session in sessions if session.visibility == "shared"]
    if not shared_sessions:
        return False
    first_shared = min(shared_sessions, key=lambda session: session.shared_at or "")
    return _is_recently_shared(first_shared)


def _render_weekly_report_panel(couple) -> None:
    # TASK-9 临时按钮，cron 稳定后另开任务删除
    active = service_active_for_couple(couple.couple_id)
    reports = list_reports(couple.couple_id)
    latest_report = reports[0] if reports else None
    status = partner_enabled_status(_uid())

    with st.expander("📊 周报", expanded=False):
        if couple.couple_status == "frozen":
            st.info("这段时间不再生成新的周报，已经留下的历史仍可以慢慢看。")
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
            if st.button("🧪 立即生成周报（测试）", width="stretch"):
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


def _pending_unlock_notice_text(unlock_at: str | None) -> str:
    unlock_dt = parse_dt(unlock_at or "")
    if not unlock_dt:
        return "开放时间待定"
    remaining = unlock_dt - datetime.now()
    if remaining.total_seconds() <= 0:
        return "即将开放"
    days = remaining.days
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    if days > 0:
        return f"还要 {days + (1 if remaining.seconds else 0)} 天 · {unlock_at}"
    if hours > 0:
        return f"还要 {hours} 小时 · {unlock_at}"
    return f"还要 {max(1, minutes)} 分钟 · {unlock_at}"


def _render_pending_unlock_preview(sessions) -> None:
    pending_sessions = sorted(
        [
            session
            for session in sessions
            if session.visibility == "pending_unlock" and session.user_id != _uid()
        ],
        key=lambda session: session.unlock_at or "",
    )
    if not pending_sessions:
        return

    with st.container(border=True):
        st.markdown("#### 有记录正在路上")
        if len(pending_sessions) == 1:
            st.caption("有一份记录会在约定的时间向你开放。")
        else:
            st.caption(f"有 {len(pending_sessions)} 份记录会在约定的时间向你开放。")
        for index, session in enumerate(pending_sessions, start=1):
            st.write(f"{index}. {_pending_unlock_notice_text(session.unlock_at)}")


def render_us_tab(db: dict) -> None:
    couple = _couple()
    if not couple:
        with st.container(border=True):
            st.markdown("#### 这里会慢慢放下你们已经开放的记录")
            st.caption("先把彼此连上。等绑定完成后，共享过的内容会按时间留在这里。")
            render_tab_jump_button(
                "去「设置」绑定伴侣",
                "⚙️ 设置",
                key="us_bind_settings",
                target_section_id=SETTINGS_BIND_SECTION_ID,
            )
        return
    if couple.couple_status == "pending_bind":
        st.info("等绑定确认后，这里会开始出现你们已经开放的记录。")
        return

    _render_weekly_report_panel(couple)
    st.divider()

    couple_sessions = list_sessions_for_couple(couple.couple_id)
    _render_pending_unlock_preview(couple_sessions)
    if _should_show_first_shared_moment(couple_sessions):
        with st.container(border=True):
            st.markdown("#### 你们的第一条共享记录来了")
            st.caption("先慢慢看看，那一刻各自留下了什么。")

    sessions = sorted(
        [
            session
            for session in couple_sessions
            if session.visibility == "shared" and can_view_session(session, _uid())
        ],
        key=lambda session: session.shared_at or "",
        reverse=True,
    )

    if not sessions:
        st.info("这里还没有已经开放的记录。等第一条到了约定时间，它会出现在这里。")
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
            author_relation="我的记录" if is_mine else "对方的记录",
            show_completion=False,
            show_recently_shared=True,
            button_label="评论",
            show_status_badge=False,
            show_description=True,
        )

        if selected_id == session.session_id:
            with target_col:
                render_comments(session, key_scope="us_inline")

    if selected_id and not any(item.session_id == selected_id for item in sessions):
        st.session_state["us_selected"] = None
