"""
OurPresent — 入口文件
启动：python -m streamlit run main.py
"""

from __future__ import annotations

import streamlit as st

from backend.application.auth import (
    AuthError,
    create_auth_token,
    login,
    register,
    validate_auth_token,
)
from backend.application.couples import is_frozen
from backend.application.maintenance import load_db_with_tick
from backend.infrastructure.database.couples_repo import get_couple_for_user
from backend.infrastructure.database.db import ensure_dirs
from backend.infrastructure.database.users_repo import get_user_by_id
from frontend.streamlit_app.components import _current_user, _partner_id
from frontend.streamlit_app.pages.tab_mine import render_mine_tab
from frontend.streamlit_app.pages.tab_settings import render_settings_tab
from frontend.streamlit_app.pages.tab_us import render_us_tab

# ─────────────────────────────────────────────────────────────────────────────
# 页面配置（必须是第一个 Streamlit 调用）
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OurPresent",
    page_icon="💑",
    layout="wide",
)


# ─────────────────────────────────────────────────────────────────────────────
# 会话状态初始化
# ─────────────────────────────────────────────────────────────────────────────
def _init_state() -> None:
    defaults = {
        "user": None,
        "upload_key": 0,
        "us_selected": None,
        "mine_selected": None,
        "auth_tab": "login",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # 刷新页面时通过 URL token 自动恢复登录
    if st.session_state["user"] is None:
        token = st.query_params.get("token")
        if token:
            user = validate_auth_token(token)
            if user:
                st.session_state["user"] = user
            else:
                del st.query_params["token"]


# ─────────────────────────────────────────────────────────────────────────────
# 登录 / 注册页
# ─────────────────────────────────────────────────────────────────────────────
def render_auth_page() -> None:
    st.title("💑 OurPresent")
    st.caption("情侣专属的情感记录空间")
    st.divider()

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        tabs = st.tabs(["登录", "注册"])

        with tabs[0]:
            with st.form("login_form"):
                uname = st.text_input("用户名")
                pwd = st.text_input("密码", type="password")
                if st.form_submit_button("登录", width="stretch", type="primary"):
                    try:
                        user = login(uname, pwd)
                        st.session_state["user"] = user
                        token = create_auth_token(user.user_id)
                        st.query_params["token"] = token
                        st.rerun()
                    except AuthError as e:
                        st.error(str(e))

        with tabs[1]:
            with st.form("register_form"):
                uname2 = st.text_input("用户名", key="reg_uname")
                pwd2 = st.text_input("密码（至少 6 位）", type="password", key="reg_pwd")
                pwd2c = st.text_input("确认密码", type="password", key="reg_pwd_c")
                if st.form_submit_button("注册", width="stretch"):
                    if pwd2 != pwd2c:
                        st.error("两次密码输入不一致")
                    else:
                        try:
                            user = register(uname2, pwd2)
                            st.success(f"注册成功！你的用户 ID 是：`{user.user_id}`")
                            st.info("请把 ID 告诉你的伴侣，登录后在「设置」里互相绑定。")
                        except AuthError as e:
                            st.error(str(e))

    with col_right:
        st.markdown("""
### 关于 OurPresent

> 在保护个人绝对隐私的前提下，通过"延时共享"沉淀情感。

**核心机制**
- 📝 记录只属于自己，默认私密
- ⏳ 申请共享时自定开放时间，到点对方才能查看
- 🔐 分手时 90 天冻结期，期满自动销毁
""")


# ─────────────────────────────────────────────────────────────────────────────
# 主函数
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    ensure_dirs()
    _init_state()

    user = _current_user()

    if not user:
        render_auth_page()
        return

    db = load_db_with_tick()

    col_title, col_user = st.columns([5, 1])
    with col_title:
        st.markdown("## 💑 OurPresent")
    with col_user:
        couple = get_couple_for_user(user.user_id)
        if couple and couple.couple_status == "active":
            partner_id = _partner_id()
            partner = get_user_by_id(partner_id) if partner_id else None
            p_name = partner.username if partner else "?"
            st.caption(f"👤 {user.username} · 💑 {p_name}")
        else:
            st.caption(f"👤 {user.username}")

    if is_frozen(user.user_id):
        st.warning("❄️ 关系处于冻结期，当前为只读状态。")

    tab_us, tab_mine, tab_settings = st.tabs(
        [
            "🏠 我们",
            "📝 我的",
            "⚙️ 设置",
        ]
    )

    with tab_us:
        render_us_tab(db)
    with tab_mine:
        render_mine_tab(db)
    with tab_settings:
        render_settings_tab(db)


if __name__ == "__main__":
    main()
