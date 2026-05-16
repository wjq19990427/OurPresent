"""Settings tab."""

from __future__ import annotations

import io
import zipfile

import streamlit as st

from backend.application.auth import revoke_auth_token
from backend.application.couples import (
    CoupleError,
    accept_bind,
    reject_bind,
    send_bind_request,
    start_uncouple,
)
from backend.application.reports import (
    list_reports,
    partner_enabled_status,
    service_active_for_couple,
)
from backend.application.sessions import collect_export_files
from backend.infrastructure.database.couples_repo import (
    get_pending_requests_for_user,
    update_couple,
)
from backend.infrastructure.database.users_repo import get_user_by_id, update_user
from frontend.streamlit_app.components import (
    SETTINGS_BIND_SECTION_ID,
    SETTINGS_REPORT_SECTION_ID,
    _couple,
    _current_user,
    _partner_id,
    render_report_history,
)

_REPORT_INTERVAL_OPTIONS = [7, 14, 30]
_REPORT_INTERVAL_LABELS = {
    7: "7 天 / 每周",
    14: "14 天 / 每两周",
    30: "30 天 / 每月",
}


def _set_settings_notice(level: str, message: str) -> None:
    st.session_state["settings_notice"] = {"level": level, "message": message}


def _render_settings_notice() -> None:
    notice = st.session_state.pop("settings_notice", None)
    if not notice:
        return
    getattr(st, notice["level"], st.info)(notice["message"])


def _run_active_uncouple_action(action: str, user_id: str) -> None:
    try:
        if action == "start":
            start_uncouple(user_id)
            _set_settings_notice(
                "warning",
                "已经进入冻结期。先把这段时间留给彼此，之后还可以再决定。",
            )
    except CoupleError as exc:
        _set_settings_notice("error", str(exc))
    st.rerun()


def _render_active_uncouple_confirm(user_id: str) -> None:
    pending_action = st.session_state.get("settings_pending_uncouple_action")
    if pending_action != "start":
        return

    st.warning("这会让关系进入 90 天冻结期。新的记录和编辑会先暂停，到期后数据会自动销毁。")
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button(
            "进入冻结期",
            key="settings_confirm_start",
            width="stretch",
            type="primary",
        ):
            st.session_state.pop("settings_pending_uncouple_action", None)
            _run_active_uncouple_action("start", user_id)
    with cancel_col:
        if st.button("先等等", key="settings_cancel_start", width="stretch"):
            st.session_state.pop("settings_pending_uncouple_action", None)
            st.rerun()


def _render_report_history_entry(couple) -> None:
    if not couple or couple.couple_status not in ("active", "frozen"):
        return
    with st.expander("查看周报历史", expanded=False):
        render_report_history(list_reports(couple.couple_id))


def _weekly_report_toggle_available(couple) -> bool:
    return bool(couple and couple.couple_status == "active")


def _render_weekly_report_section(user, couple) -> None:
    st.markdown(f"<div id='{SETTINGS_REPORT_SECTION_ID}'></div>", unsafe_allow_html=True)
    st.markdown("### 📊 情感周报服务")
    st.caption("周报基于你们已共享的记录生成，不读私密内容。")
    toggle_available = _weekly_report_toggle_available(couple)
    toggle_value = (
        user.weekly_report_enabled
        if couple and couple.couple_status in ("active", "frozen")
        else False
    )
    enabled = st.checkbox(
        "开启我的情感周报服务",
        value=toggle_value,
        disabled=not toggle_available,
        help="绑定伴侣后，双方都开启，才会为你们的共享记录生成周报。",
    )
    if toggle_available and enabled != user.weekly_report_enabled:
        updated = update_user(user.user_id, {"weekly_report_enabled": enabled})
        if updated:
            st.session_state["user"] = updated
        st.rerun()

    status = partner_enabled_status(user.user_id)
    if not couple:
        st.caption("（未绑定伴侣）")
        st.info("先完成伴侣绑定，之后这里才会打开。")
        return
    if couple.couple_status == "pending_bind":
        st.caption("（等待绑定确认）")
        st.info("等绑定确认后，你们再一起决定是否开启周报。")
        return
    if couple.couple_status == "frozen":
        st.info("这段时间不再生成新的周报；已经留下的历史仍可查看。")
        _render_report_history_entry(couple)
        return

    if status in ("both", "only_partner"):
        st.success("✅ 对方已开启")
    else:
        st.info("⌛ 对方尚未开启")

    if service_active_for_couple(couple.couple_id):
        current_interval = couple.weekly_report_interval_days
        index = (
            _REPORT_INTERVAL_OPTIONS.index(current_interval)
            if current_interval in _REPORT_INTERVAL_OPTIONS
            else 0
        )
        selected_interval = st.selectbox(
            "周报频率",
            _REPORT_INTERVAL_OPTIONS,
            index=index,
            format_func=lambda days: _REPORT_INTERVAL_LABELS[days],
            help="频率会影响下一次自动生成的节奏。",
        )
        if selected_interval != current_interval:
            update_couple(couple.couple_id, {"weekly_report_interval_days": selected_interval})
            st.rerun()
    else:
        st.caption("两人都开启后，可以一起约定周报频率。")
    _render_report_history_entry(couple)


def render_settings_tab(db: dict) -> None:
    user = _current_user()
    couple = _couple()
    _render_settings_notice()

    st.markdown("### 我的资料")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**用户名**：{user.username}")
        st.markdown(f"**用户 ID**：`{user.user_id}`")
        st.caption("把上方 ID 分享给伴侣，让对方来搜索你。")
    with col_b:
        if st.button("退出登录", width="stretch"):
            token = st.query_params.get("token")
            if token:
                revoke_auth_token(token)
                del st.query_params["token"]
            st.session_state["user"] = None
            st.rerun()

    st.divider()
    _render_weekly_report_section(user, couple)
    st.divider()

    pending_reqs = get_pending_requests_for_user(user.user_id)
    if pending_reqs:
        st.markdown("### 📩 收到的绑定请求")
        for req in pending_reqs:
            sender = get_user_by_id(req.user_a)
            sender_name = sender.username if sender else req.user_a
            st.info(f"**{sender_name}** (`{req.user_a}`) 想与你绑定")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "✅ 接受",
                    key=f"accept_{req.couple_id}",
                    width="stretch",
                    type="primary",
                ):
                    accept_bind(req.couple_id)
                    st.success("绑定成功！")
                    st.rerun()
            with col2:
                if st.button("❌ 拒绝", key=f"reject_{req.couple_id}", width="stretch"):
                    reject_bind(req.couple_id)
                    st.info("已拒绝。")
                    st.rerun()
        st.divider()

    st.markdown(f"<div id='{SETTINGS_BIND_SECTION_ID}'></div>", unsafe_allow_html=True)
    st.markdown("### 💑 伴侣绑定")

    if not couple:
        with st.form("bind_form"):
            target_id = st.text_input(
                "输入伴侣的用户 ID",
                placeholder="usr_xxxxxxxx",
                help="让伴侣在「设置」里找到自己的 ID 并告诉你",
            )
            if st.form_submit_button("发送绑定请求", width="stretch", type="primary"):
                try:
                    send_bind_request(user.user_id, target_id.strip())
                    st.success("绑定请求已发送，等待对方确认。")
                    st.rerun()
                except CoupleError as exc:
                    st.error(str(exc))

    elif couple.couple_status == "pending_bind":
        is_sender = couple.user_a == user.user_id
        if is_sender:
            partner = get_user_by_id(couple.user_b)
            partner_name = partner.username if partner else couple.user_b
            st.info(f"⌛ 已向 **{partner_name}** 发出绑定请求，等待对方在「设置」里确认……")
        else:
            st.warning(
                "👆 你收到了绑定邀请，请在上方「收到的绑定请求」区点击 **接受** 或 **拒绝**。"
            )

    elif couple.couple_status == "active":
        partner_id = _partner_id()
        partner = get_user_by_id(partner_id) if partner_id else None
        partner_name = partner.username if partner else "对方"
        st.success(f"✅ 已与 **{partner_name}** 绑定")
        st.caption(f"绑定时间：{couple.created_at}")

        with st.expander("⚠️ 解除绑定", expanded=False):
            st.info("如果想停下来冷静一段时间，可以先进入 90 天冻结期。")
            if st.button("进入冻结期", width="stretch", type="secondary"):
                st.session_state["settings_pending_uncouple_action"] = "start"
                st.rerun()
            _render_active_uncouple_confirm(user.user_id)

    elif couple.couple_status == "frozen":
        st.info("撤回冻结、申请现在分手，或回应对方的请求，都可以直接在页面顶部的冻结提示里操作。")

        st.markdown("---")
        st.markdown("#### 📦 导出我的数据")
        st.caption("如果想把自己的文件和文字留一份在手边，可以在这里导出；不包含对方的数据。")
        if st.button("生成导出包", width="stretch"):
            export_files = collect_export_files(user.user_id)
            if not export_files:
                st.info("没有可导出的文件。")
            else:
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for file_path in export_files:
                        zip_file.write(file_path, arcname=file_path.name)
                buf.seek(0)
                st.download_button(
                    label=f"下载 ZIP（共 {len(export_files)} 个文件）",
                    data=buf,
                    file_name=f"ourpresent_export_{user.user_id}.zip",
                    mime="application/zip",
                )

    st.divider()
