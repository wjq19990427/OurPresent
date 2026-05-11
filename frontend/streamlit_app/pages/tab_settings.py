"""Settings tab."""

from __future__ import annotations

import io
import zipfile

import streamlit as st

from backend.application.auth import revoke_auth_token
from backend.application.couples import (
    CoupleError,
    accept_bind,
    confirm_uncouple,
    reject_bind,
    send_bind_request,
    start_uncouple,
)
from backend.application.reports import partner_enabled_status, service_active_for_couple
from backend.application.sessions import collect_export_files
from backend.infrastructure.database.couples_repo import (
    get_pending_requests_for_user,
    update_couple,
)
from backend.infrastructure.database.users_repo import get_user_by_id, update_user
from frontend.streamlit_app.components import _couple, _current_user, _partner_id

_REPORT_INTERVAL_OPTIONS = [7, 14, 30]


def _render_weekly_report_section(user, couple) -> None:
    st.markdown("### 📊 情感周报服务")
    enabled = st.checkbox(
        "开启我的情感周报服务",
        value=user.weekly_report_enabled,
        help="双方都开启后，才会为你们的共享记录生成周报。",
    )
    if enabled != user.weekly_report_enabled:
        updated = update_user(user.user_id, {"weekly_report_enabled": enabled})
        if updated:
            st.session_state["user"] = updated
        st.rerun()

    status = partner_enabled_status(user.user_id)
    if not couple or couple.couple_status != "active":
        st.caption("（未绑定伴侣）")
        st.info("绑定伴侣后，两人都开启即可生效。")
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
            format_func=lambda days: f"每 {days} 天",
        )
        if selected_interval != current_interval:
            update_couple(couple.couple_id, {"weekly_report_interval_days": selected_interval})
            st.rerun()
    else:
        st.caption("两人都开启后，可以一起约定周报频率。")


def render_settings_tab(db: dict) -> None:
    user = _current_user()
    couple = _couple()

    st.markdown("### 我的资料")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**用户名**：{user.username}")
        st.markdown(f"**用户 ID**：`{user.user_id}`")
        st.caption("把上方 ID 分享给伴侣，让对方来搜索你。")
    with col_b:
        if st.button("退出登录", use_container_width=True):
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
                    use_container_width=True,
                    type="primary",
                ):
                    accept_bind(req.couple_id)
                    st.success("绑定成功！")
                    st.rerun()
            with col2:
                if st.button("❌ 拒绝", key=f"reject_{req.couple_id}", use_container_width=True):
                    reject_bind(req.couple_id)
                    st.info("已拒绝。")
                    st.rerun()
        st.divider()

    st.markdown("### 💑 伴侣绑定")

    if not couple:
        with st.form("bind_form"):
            target_id = st.text_input(
                "输入伴侣的用户 ID",
                placeholder="usr_xxxxxxxx",
                help="让伴侣在「设置」里找到自己的 ID 并告诉你",
            )
            if st.form_submit_button("发送绑定请求", use_container_width=True, type="primary"):
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
            st.warning(
                (
                    "**单方发起**：进入 90 天冻结期。应用变为只读，"
                    "冻结期满后**所有数据将被永久销毁**。\n\n"
                    "**双方同意**：立即销毁全部数据，无法恢复。"
                )
            )
            col_single, col_mutual = st.columns(2)
            with col_single:
                if st.button(
                    "😔 进入冻结期", use_container_width=True, type="secondary"
                ):
                    start_uncouple(user.user_id)
                    st.warning("已进入冻结期，90 天后数据将被销毁。")
                    st.rerun()
            with col_mutual:
                if st.button(
                    "💔 双方同意立即销毁", use_container_width=True, type="secondary"
                ):
                    confirm_uncouple(user.user_id)
                    st.error("已销毁全部数据。")
                    st.session_state["user"] = None
                    st.rerun()

    elif couple.couple_status == "frozen":
        ends_at = couple.freeze_ends_at or ""
        st.error(f"❄️ 关系处于冻结期，到期时间：**{ends_at}**，到期后数据将被自动销毁。")
        st.info("冻结期内应用为只读状态，无法上传或编辑内容。")

        st.markdown("---")
        st.markdown("#### 📦 导出我的数据")
        st.caption("冻结期内可导出属于自己的文件和文字记录，不包含对方数据。")
        if st.button("生成导出包", use_container_width=True):
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
