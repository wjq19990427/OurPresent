"""Us tab - shared couple timeline."""

from __future__ import annotations

import streamlit as st

from backend.application.reports import (
    generate_weekly_report,
    get_latest_ready_report,
    partner_enabled_status,
    service_active_for_couple,
)
from backend.application.sessions import can_view_session
from backend.domain.models import Report
from backend.infrastructure.database.sessions_repo import list_sessions_for_couple
from backend.infrastructure.database.users_repo import get_user_by_id
from frontend.streamlit_app.components import _couple, _uid, render_card, render_detail


def _username(user_id: str) -> str:
    user = get_user_by_id(user_id)
    return user.username if user else user_id


def _render_report_footprint(report: Report) -> None:
    footprint = report.footprint
    col_total, col_days, col_comments = st.columns(3)
    col_total.metric("共享记录", footprint.get("total", 0))
    col_days.metric("活跃天数", footprint.get("active_days", 0))
    col_comments.metric("评论", footprint.get("comment_count", 0))

    by_kind = footprint.get("by_kind", {})
    if by_kind:
        st.caption(
            " · ".join(
                [
                    f"图片 {by_kind.get('photo', 0)}",
                    f"视频 {by_kind.get('video', 0)}",
                    f"文字 {by_kind.get('text', 0)}",
                ]
            )
        )


def _render_report_weather(report: Report) -> None:
    weather = report.weather or {}
    if not weather:
        return
    st.markdown("#### 情绪气象站")
    narrative = weather.get("narrative", "")
    if narrative:
        st.info(narrative)
    tags = weather.get("tags", [])
    for tag in tags:
        label = tag.get("label", "")
        weight = float(tag.get("weight", 0) or 0)
        phase = tag.get("phase", "")
        st.caption(f"{label} · {phase}")
        st.progress(max(0.0, min(weight, 1.0)))


def _render_report_resonance(report: Report) -> None:
    if not report.resonance:
        return
    st.markdown("#### 同频与共鸣瞬间")
    for item in report.resonance:
        with st.container(border=True):
            st.caption(item.get("day", ""))
            st.markdown(f"**{item.get('topic', '同日共享')}**")
            left, right = st.columns(2)
            left.write(item.get("user_a_excerpt", ""))
            right.write(item.get("user_b_excerpt", ""))


def _kind_icon(kind: str) -> str:
    return {"photo": "🖼", "video": "🎞", "text": "📝"}.get(kind, "📎")


def _render_report_suspense(report: Report) -> None:
    if not report.suspense:
        return
    st.markdown("#### 未尽的悬念")
    for item in report.suspense:
        icon = _kind_icon(item.get("kind", ""))
        st.caption(
            f"{icon} 还剩 {item.get('days_remaining', 0)} 天 · "
            f"{item.get('unlock_at', '未设置时间')}"
        )


def _render_latest_report(report: Report) -> None:
    st.caption(f"{report.window_start} → {report.window_end}")
    _render_report_footprint(report)
    if report.status == "sparse":
        st.info("这周共享记录较少，留些空白也好。")
        return
    _render_report_weather(report)
    _render_report_resonance(report)
    _render_report_suspense(report)


def _render_weekly_report_panel(couple_id: str) -> None:
    # TASK-9 临时按钮，cron 稳定后另开任务删除
    active = service_active_for_couple(couple_id)
    latest_report = get_latest_ready_report(couple_id)
    status = partner_enabled_status(_uid())

    with st.expander("📊 周报", expanded=False):
        if active:
            # TASK-9 临时按钮，cron 稳定后另开任务删除
            if st.button("🧪 立即生成周报（测试）", use_container_width=True):
                generate_weekly_report(couple_id)
                st.rerun()
            st.caption("（临时入口，cron 稳定后将由架构师删除）")

        if latest_report:
            _render_latest_report(latest_report)
        elif status == "both":
            st.info("邀请你写下第一周的共享记录。")
        elif status == "only_partner":
            st.info("对方已开启周报，要不要一起开启？去「设置」里打开你的开关。")
        elif status == "only_self":
            st.info("⌛ 等待对方一同开启。你们都开启后，这里会出现属于你们的情感周报。")
        else:
            st.info("开启情感周报后，可以一起回看共享记录里的关系足迹。")


def render_us_tab(db: dict) -> None:
    couple = _couple()
    if not couple or couple.couple_status != "active":
        st.info("先去「设置」里绑定伴侣。")
        return

    _render_weekly_report_panel(couple.couple_id)
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
