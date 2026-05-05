"""
Tab 5 — ⚙️ 账户设置（绑定请求、情侣关系面板、解绑协议、数据导出）
"""

from __future__ import annotations

import io
import zipfile

import streamlit as st

from backend.db_manager import (
    get_user_by_id,
    get_pending_requests_for_user,
    revoke_auth_token,
)
from backend.session_manager import collect_export_files
from backend.auth_manager import (
    AuthError, CoupleError,
    send_bind_request, accept_bind, reject_bind,
    start_uncouple, confirm_uncouple,
)
from frontend.components import _current_user, _uid, _couple, _partner_id


def render_account_tab(db: dict) -> None:
    user   = _current_user()
    couple = _couple()

    # ── 用户信息 ──
    st.markdown("### 我的账户")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**用户名**：{user['username']}")
        st.markdown(f"**用户 ID**：`{user['user_id']}`")
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

    # ── 待处理的绑定请求 ──
    pending_reqs = get_pending_requests_for_user(user["user_id"])
    if pending_reqs:
        st.markdown("### 📩 收到的绑定请求")
        for req in pending_reqs:
            sender      = get_user_by_id(req["user_a"])
            sender_name = sender["username"] if sender else req["user_a"]
            st.info(f"**{sender_name}** (`{req['user_a']}`) 想与你绑定")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 接受", key=f"accept_{req['couple_id']}",
                             use_container_width=True, type="primary"):
                    accept_bind(req["couple_id"])
                    st.success("绑定成功！")
                    st.rerun()
            with col2:
                if st.button("❌ 拒绝", key=f"reject_{req['couple_id']}",
                             use_container_width=True):
                    reject_bind(req["couple_id"])
                    st.info("已拒绝。")
                    st.rerun()
        st.divider()

    # ── 情侣关系面板 ──
    st.markdown("### 💑 情侣关系")

    if not couple:
        with st.form("bind_form"):
            target_id = st.text_input(
                "输入伴侣的用户 ID",
                placeholder="usr_xxxxxxxx",
                help="让伴侣在「账户」页找到自己的 ID 并告诉你",
            )
            if st.form_submit_button("发送绑定请求", use_container_width=True, type="primary"):
                try:
                    send_bind_request(user["user_id"], target_id.strip())
                    st.success("绑定请求已发送，等待对方确认。")
                    st.rerun()
                except CoupleError as e:
                    st.error(str(e))

    elif couple["couple_status"] == "pending_bind":
        is_sender = couple["user_a"] == user["user_id"]
        if is_sender:
            partner      = get_user_by_id(couple["user_b"])
            partner_name = partner["username"] if partner else couple["user_b"]
            st.info(f"⌛ 已向 **{partner_name}** 发出绑定请求，等待对方在「账户」页确认……")
        else:
            st.warning("👆 你收到了绑定邀请，请在上方「收到的绑定请求」区点击 **接受** 或 **拒绝**。")

    elif couple["couple_status"] == "active":
        partner_id   = _partner_id()
        partner      = get_user_by_id(partner_id) if partner_id else None
        partner_name = partner["username"] if partner else "对方"
        st.success(f"✅ 已与 **{partner_name}** 绑定")
        st.caption(f"绑定时间：{couple.get('created_at', '')}")

        with st.expander("⚠️ 解除绑定（分手协议）", expanded=False):
            st.warning(
                "**单方发起**：进入 90 天冻结期。应用变为只读，冻结期满后**所有数据将被永久销毁**。\n\n"
                "**双方同意**：立即销毁全部数据，无法恢复。"
            )
            col_s, col_m = st.columns(2)
            with col_s:
                if st.button("😔 我要分手（进入冻结期）",
                             use_container_width=True, type="secondary"):
                    start_uncouple(user["user_id"])
                    st.warning("已进入冻结期，90 天后数据将被销毁。")
                    st.rerun()
            with col_m:
                if st.button("💔 我们双方都同意（立即销毁）",
                             use_container_width=True, type="secondary"):
                    confirm_uncouple(user["user_id"])
                    st.error("已销毁全部数据。")
                    st.session_state["user"] = None
                    st.rerun()

    elif couple["couple_status"] == "frozen":
        ends_at = couple.get("freeze_ends_at", "")
        st.error(f"❄️ 关系处于冻结期，到期时间：**{ends_at}**，到期后数据将被自动销毁。")
        st.info("冻结期内应用为只读状态，无法上传或编辑内容。")

        st.markdown("---")
        st.markdown("#### 📦 导出我的数据")
        st.caption("冻结期内可导出属于自己的文件和文字记录，不包含对方数据。")
        if st.button("生成导出包", use_container_width=True):
            export_files = collect_export_files(user["user_id"])
            if not export_files:
                st.info("没有可导出的文件。")
            else:
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fp in export_files:
                        zf.write(fp, arcname=fp.name)
                buf.seek(0)
                st.download_button(
                    label=f"下载 ZIP（共 {len(export_files)} 个文件）",
                    data=buf,
                    file_name=f"ourpresent_export_{user['user_id']}.zip",
                    mime="application/zip",
                )

    st.divider()
