"""
OurPresent — UI 层（Streamlit）
启动：python -m streamlit run app.py
"""

from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

import auth as auth_module
import db as db_module
from db import FIELD_SCHEMA, ASSETS_DIR, PENDING_DIR, FINAL_DIR

try:
    import cv2
    from PIL import Image
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# 页面配置
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OurPresent",
    page_icon="💑",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# session_state 初始化
# ─────────────────────────────────────────────────────────────────────────────
def _init_state() -> None:
    defaults = {
        "user":               None,
        "upload_key":         0,
        "pending_selected":   None,
        "archived_selected":  None,
        "shared_selected":    None,
        "auth_tab":           "login",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # 刷新页面时通过 URL token 自动恢复登录
    if st.session_state["user"] is None:
        token = st.query_params.get("token")
        if token:
            user = db_module.validate_auth_token(token)
            if user:
                st.session_state["user"] = user
            else:
                # token 已过期，清理 URL
                del st.query_params["token"]


# ─────────────────────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────────────────────
def _current_user() -> Optional[dict]:
    return st.session_state.get("user")


def _uid() -> str:
    return _current_user()["user_id"]


def _is_frozen() -> bool:
    return auth_module.is_frozen(_uid())


def _couple() -> Optional[dict]:
    return db_module.get_couple_for_user(_uid())


def _partner_id() -> Optional[str]:
    c = _couple()
    if not c or c.get("couple_status") != "active":
        return None
    return c["user_b"] if c["user_a"] == _uid() else c["user_a"]


def _session_thumb(session: dict):
    """返回 (PIL Image | None, label: str)。"""
    if not _CV2_AVAILABLE:
        return None, "⚠ 预览不可用（缺少 cv2/PIL）"
    files = session.get("files", [])
    if not files:
        text = session.get("description", "")
        return None, (text[:80] + "…") if len(text) > 80 else text
    first = Path(files[0]["path"])
    ext   = first.suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        try:
            return Image.open(first), ""
        except Exception:
            return None, "图片读取失败"
    if ext == ".mp4":
        return _video_thumb(first)
    if ext in db_module.TEXT_EXTS:
        try:
            preview = first.read_text(encoding="utf-8", errors="ignore")[:80]
            return None, preview
        except Exception:
            return None, "文本读取失败"
    return None, f"📎 {files[0]['original_name']}"


def _video_thumb(path: Path):
    try:
        cap = cv2.VideoCapture(str(path))
        ok, frame = cap.read()
        cap.release()
        if not ok:
            return None, "视频读取失败"
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 120, 24], fill="black")
        draw.text((4, 4), "▶ [视频]", fill="white")
        return img, ""
    except Exception:
        return None, "视频缩略图失败"


def _pil_to_bytes(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _days_until_unlock(session: dict) -> int:
    upload_dt = db_module._parse_dt(session.get("upload_time", ""))
    if not upload_dt:
        return 90
    elapsed = (datetime.now() - upload_dt).days
    return max(0, 90 - elapsed)


def _visibility_badge(session: dict) -> str:
    v = session.get("visibility", "private")
    if v == "private":
        return "🔒 私密"
    if v == "pending_unlock":
        days = _days_until_unlock(session)
        return f"⏳ 待解锁（还需 {days} 天）"
    return "✅ 已共享"


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
                pwd   = st.text_input("密码", type="password")
                if st.form_submit_button("登录", use_container_width=True, type="primary"):
                    try:
                        user = auth_module.login(uname, pwd)
                        st.session_state["user"] = user
                        token = db_module.create_auth_token(user["user_id"])
                        st.query_params["token"] = token
                        st.rerun()
                    except auth_module.AuthError as e:
                        st.error(str(e))

        with tabs[1]:
            with st.form("register_form"):
                uname2 = st.text_input("用户名", key="reg_uname")
                pwd2   = st.text_input("密码（至少 6 位）", type="password", key="reg_pwd")
                pwd2c  = st.text_input("确认密码", type="password", key="reg_pwd_c")
                if st.form_submit_button("注册", use_container_width=True):
                    if pwd2 != pwd2c:
                        st.error("两次密码输入不一致")
                    else:
                        try:
                            user = auth_module.register(uname2, pwd2)
                            st.success(f"注册成功！你的用户 ID 是：`{user['user_id']}`")
                            st.info("请把 ID 告诉你的伴侣，登录后在「账户」页互相绑定。")
                        except auth_module.AuthError as e:
                            st.error(str(e))

    with col_right:
        st.markdown("""
### 关于 OurPresent

> 在保护个人绝对隐私的前提下，通过"延时共享"沉淀情感。

**核心机制**
- 📝 记录只属于自己，默认私密
- ⏳ 授权后满 90 天，对方才能查看
- 🔐 分手时 90 天冻结期，期满自动销毁
""")


# ─────────────────────────────────────────────────────────────────────────────
# 字段渲染（表单内）
# ─────────────────────────────────────────────────────────────────────────────
def render_field_inputs(
    prefix: str,
    defaults: Optional[dict] = None,
    skip_keys: Optional[set] = None,
) -> dict:
    skip_keys = skip_keys or set()
    defaults  = defaults or {}
    result    = {}
    for f in FIELD_SCHEMA:
        key = f["key"]
        if key in skip_keys:
            result[key] = defaults.get(key, "")
            continue
        label       = f["label"] + (" *" if f["required"] else "")
        default_val = defaults.get(key, "")
        wkey        = f"{prefix}_{key}"

        if f["type"] == "textarea":
            result[key] = st.text_area(
                label, value=default_val, placeholder=f.get("placeholder", ""),
                help=f.get("help", ""), key=wkey,
            )
        elif f["type"] == "date_or_text":
            sub_col1, sub_col2 = st.columns([1, 1])
            with sub_col1:
                free = st.text_input(
                    label, value=default_val if not _looks_like_date(default_val) else "",
                    placeholder=f.get("placeholder", ""),
                    help="可自由输入，如「2023年春天」", key=wkey + "_free",
                )
            with sub_col2:
                try:
                    date_default = datetime.strptime(default_val, "%Y-%m-%d").date() if _looks_like_date(default_val) else None
                except ValueError:
                    date_default = None
                picked = st.date_input(
                    "或选择日期", value=date_default, key=wkey + "_date",
                )
            result[key] = free.strip() if free.strip() else (str(picked) if picked else "")
        else:
            result[key] = st.text_input(
                label, value=default_val, placeholder=f.get("placeholder", ""),
                help=f.get("help", ""), key=wkey,
            )
    return result


def _looks_like_date(s: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", s or ""))


# ─────────────────────────────────────────────────────────────────────────────
# 评论区渲染（form 外部）
# ─────────────────────────────────────────────────────────────────────────────
def render_comments(session: dict) -> None:
    st.markdown("#### 💬 评论区")
    comments = session.get("comments", [])
    if not comments:
        st.caption("暂无评论")
    for c in comments:
        author_obj = db_module.get_user_by_id(c.get("author", ""))
        author_name = author_obj["username"] if author_obj else c.get("author", "")
        col_t, col_del = st.columns([9, 1])
        with col_t:
            st.markdown(f"**{author_name}** · {c['created_at']}\n\n{c['text']}")
        with col_del:
            if st.button("🗑", key=f"del_cmt_{c['id']}", help="删除评论"):
                db_module.delete_comment(session["session_id"], c["id"])
                st.rerun()
    st.divider()
    cmt_key = f"new_cmt_{session['session_id']}"
    new_text = st.text_area("写下评论……", key=cmt_key, height=80)
    if st.button("发送评论", key=f"send_cmt_{session['session_id']}"):
        if new_text.strip():
            db_module.add_comment(session["session_id"], _uid(), new_text.strip())
            del st.session_state[cmt_key]
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Session 卡片
# ─────────────────────────────────────────────────────────────────────────────
def render_card(col, session: dict, state_key: str) -> None:
    with col:
        thumb, label = _session_thumb(session)
        if thumb:
            st.image(_pil_to_bytes(thumb), use_container_width=True)
        else:
            st.markdown(f"```\n{label[:120]}\n```")

        n_files    = len(session.get("files", []))
        n_comments = len(session.get("comments", []))
        st.caption(
            f"📎 {n_files}  💬 {n_comments}  ·  {session.get('upload_time', '')[:10]}"
        )
        st.caption(_visibility_badge(session))

        missing = db_module.validate_session(session)
        if missing:
            st.warning(f"⚠ 待补充：{', '.join(missing)}", icon=None)
        else:
            st.success("✅ 信息完整", icon=None)

        btn_label = "查看/编辑" if session.get("user_id") == _uid() else "查看"
        if st.button(btn_label, key=f"sel_{state_key}_{session['session_id']}",
                     use_container_width=True):
            st.session_state[state_key] = session["session_id"]
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Session 详情区
# ─────────────────────────────────────────────────────────────────────────────
def render_detail(session: dict, mode: str, read_only: bool = False) -> None:
    """
    mode: "pending" | "final" | "shared"
    read_only: 冻结期或查看对方共享内容时为 True
    """
    is_mine    = session.get("user_id") == _uid()
    is_text_s  = db_module._is_text_session(session)
    skip_keys  = {"description"} if is_text_s else set()

    # 文件预览
    with st.expander("📁 文件预览", expanded=False):
        for f in session.get("files", []):
            fp  = Path(f["path"])
            ext = fp.suffix.lower()
            st.markdown(f"**{f['original_name']}**")
            if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"} and fp.exists():
                st.image(str(fp), use_container_width=True)
            elif ext == ".mp4" and fp.exists():
                st.video(str(fp))
            elif ext in db_module.TEXT_EXTS and fp.exists():
                st.text(fp.read_text(encoding="utf-8", errors="ignore")[:2000])
            else:
                st.caption(f"📎 {f['original_name']} — 不支持预览")

    # 编辑历史（Final 专有）
    if mode == "final" and session.get("edit_history"):
        with st.expander("🕐 编辑历史", expanded=False):
            for h in reversed(session["edit_history"]):
                st.markdown(f"**{h['edited_at']}**")
                for k, v in h["changes"].items():
                    lbl = next((f["label"] for f in FIELD_SCHEMA if f["key"] == k), k)
                    st.markdown(f"- {lbl}：`{v['from']}` → `{v['to']}`")

    # 可见性控制（只有自己的记录才显示）
    if is_mine and not read_only:
        vis = session.get("visibility", "private")
        st.markdown("---")
        st.markdown(f"**隐私状态**：{_visibility_badge(session)}")
        if vis == "private":
            if st.button("📤 申请共享给对方（90天后生效）",
                         key=f"unlock_{session['session_id']}"):
                db_module.request_unlock(session["session_id"])
                st.success("已申请，满 90 天后对方可见。")
                st.rerun()
        elif vis == "pending_unlock":
            if st.button("↩️ 撤回共享申请", key=f"revoke_{session['session_id']}"):
                db_module.revoke_unlock(session["session_id"])
                st.info("已撤回，记录恢复为私密状态。")
                st.rerun()

    if is_text_s:
        st.info("📝 纯文字记录：描述字段由内容自动填充，不可手动修改。")

    st.markdown("---")

    if read_only:
        # 只读模式：直接展示字段值
        for f in FIELD_SCHEMA:
            if f["key"] in skip_keys:
                continue
            val = session.get(f["key"], "")
            if val:
                st.markdown(f"**{f['label']}**：{val}")
    else:
        # 编辑模式
        with st.form(key=f"detail_form_{session['session_id']}_{mode}"):
            new_vals = render_field_inputs(
                prefix=f"edit_{session['session_id']}",
                defaults=session,
                skip_keys=skip_keys,
            )

            col_save, col_archive, col_cancel = st.columns([2, 2, 1])
            saved = False

            with col_save:
                if st.form_submit_button("💾 保存更改", use_container_width=True):
                    db_module.update_session_fields(session["session_id"], new_vals)
                    st.success("已保存")
                    saved = True

            if mode == "pending":
                with col_archive:
                    if st.form_submit_button("✅ 完成并归档", use_container_width=True,
                                             type="primary"):
                        db_module.update_session_fields(session["session_id"], new_vals)
                        missing = db_module.validate_session({**session, **new_vals})
                        if missing:
                            st.error(f"请先填写：{', '.join(missing)}")
                        else:
                            db_module.move_to_final(session["session_id"])
                            st.session_state["pending_selected"] = None
                            st.success("已归档！")
                            saved = True

            with col_cancel:
                if st.form_submit_button("取消"):
                    st.session_state[f"{mode}_selected"] = None
                    st.rerun()

            if saved:
                st.rerun()

    # 评论区（form 外部）
    render_comments(session)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 1 — 记录舱
# ─────────────────────────────────────────────────────────────────────────────
def render_upload_tab() -> None:
    if _is_frozen():
        st.warning("⚠️ 当前处于冻结期，应用为只读状态，无法上传新内容。")
        return

    user   = _current_user()
    couple = _couple()
    couple_id = couple["couple_id"] if couple and couple.get("couple_status") == "active" else None

    mode = st.radio("上传方式", ["上传文件", "粘贴文字"], horizontal=True,
                    key=f"upload_mode_{st.session_state['upload_key']}")

    file_data_list: list[tuple[bytes, str]] = []
    source_type = "file"
    auto_description = ""

    if mode == "上传文件":
        files = st.file_uploader(
            "选择文件（支持 jpg/png/mp4/txt/md）",
            type=["jpg", "jpeg", "png", "mp4", "txt", "md"],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state['upload_key']}",
        )
        if files:
            for f in files:
                file_data_list.append((f.read(), f.name))
            # 全为文本时自动填充描述
            all_text = all(
                Path(f.name).suffix.lower() in db_module.TEXT_EXTS for f in files
            )
            if all_text:
                try:
                    auto_description = files[0].read().decode("utf-8", errors="ignore")[:500]
                    files[0].seek(0)
                except Exception:
                    auto_description = ""
    else:
        source_type = "text"
        pasted = st.text_area(
            "在此粘贴文字",
            height=200,
            key=f"paste_{st.session_state['upload_key']}",
        )
        if pasted.strip():
            safe_name = re.sub(r'[\\/:*?"<>|]', "_", pasted.strip()[:20]) + ".txt"
            file_data_list = [(pasted.encode("utf-8"), safe_name)]
            auto_description = pasted.strip()

    if not file_data_list:
        st.info("请先选择文件或粘贴文字。")
        return

    st.divider()
    with st.form(key=f"upload_form_{st.session_state['upload_key']}"):
        st.markdown("**填写信息**")
        skip = {"description"} if auto_description else set()
        if auto_description:
            st.info(f"📝 描述已自动填充：{auto_description[:60]}{'…' if len(auto_description) > 60 else ''}")

        defaults = {"description": auto_description}
        field_vals = render_field_inputs("upload", defaults=defaults, skip_keys=skip)
        if auto_description:
            field_vals["description"] = auto_description

        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("✅ 完成并归档", use_container_width=True, type="primary"):
                missing = db_module.validate_session(field_vals)
                if missing:
                    st.error(f"请先填写：{', '.join(missing)}")
                else:
                    db_module.save_session_final(
                        _uid(), couple_id, file_data_list, source_type, field_vals
                    )
                    st.session_state["upload_key"] += 1
                    st.success("已归档！")
                    st.rerun()
        with col2:
            if st.form_submit_button("📦 暂存到待处理", use_container_width=True):
                db_module.save_session_pending(
                    _uid(), couple_id, file_data_list, source_type, field_vals
                )
                st.session_state["upload_key"] += 1
                missing = db_module.validate_session(field_vals)
                if missing:
                    st.warning(f"已暂存，待补充：{', '.join(missing)}")
                else:
                    st.success("已暂存！")
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Tab 2 — 灵感墙（待处理）
# ─────────────────────────────────────────────────────────────────────────────
def render_pending_tab(db: dict) -> None:
    sessions = sorted(
        [s for s in db["sessions"] if s.get("status") == "pending" and s.get("user_id") == _uid()],
        key=lambda s: s.get("upload_time", ""),
        reverse=True,
    )
    if not sessions:
        st.info("暂无待处理记录。")
        return

    selected_id = st.session_state.get("pending_selected")

    # 卡片网格
    cols = st.columns(3)
    for i, s in enumerate(sessions):
        render_card(cols[i % 3], s, "pending_selected")

    # 详情区
    if selected_id:
        session = next((s for s in sessions if s["session_id"] == selected_id), None)
        if session:
            st.divider()
            st.markdown(f"### 详情 — {selected_id}")
            render_detail(session, mode="pending", read_only=_is_frozen())
        else:
            st.session_state["pending_selected"] = None


# ─────────────────────────────────────────────────────────────────────────────
# Tab 3 — 已归档
# ─────────────────────────────────────────────────────────────────────────────
def render_archived_tab(db: dict) -> None:
    sessions = sorted(
        [s for s in db["sessions"] if s.get("status") == "final" and s.get("user_id") == _uid()],
        key=lambda s: s.get("upload_time", ""),
        reverse=True,
    )
    if not sessions:
        st.info("暂无已归档记录。")
        return

    selected_id = st.session_state.get("archived_selected")

    cols = st.columns(3)
    for i, s in enumerate(sessions):
        render_card(cols[i % 3], s, "archived_selected")

    if selected_id:
        session = next((s for s in sessions if s["session_id"] == selected_id), None)
        if session:
            st.divider()
            st.markdown(f"### 详情 — {selected_id}")
            render_detail(session, mode="final", read_only=_is_frozen())
        else:
            st.session_state["archived_selected"] = None


# ─────────────────────────────────────────────────────────────────────────────
# Tab 4 — 情侣空间（对方共享给我的）
# ─────────────────────────────────────────────────────────────────────────────
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
            and auth_module.can_view_session(s, _uid())
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
            partner = db_module.get_user_by_id(partner_id)
            partner_name = partner["username"] if partner else partner_id
            st.markdown(f"### {partner_name} 的记录 — {selected_id}")
            render_detail(session, mode="final", read_only=True)
        else:
            st.session_state["shared_selected"] = None


# ─────────────────────────────────────────────────────────────────────────────
# Tab 5 — 账户设置
# ─────────────────────────────────────────────────────────────────────────────
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
                db_module.revoke_auth_token(token)
                del st.query_params["token"]
            st.session_state["user"] = None
            st.rerun()

    st.divider()

    # ── 待处理的绑定请求 ──
    pending_reqs = db_module.get_pending_requests_for_user(user["user_id"])
    if pending_reqs:
        st.markdown("### 📩 收到的绑定请求")
        for req in pending_reqs:
            sender = db_module.get_user_by_id(req["user_a"])
            sender_name = sender["username"] if sender else req["user_a"]
            st.info(f"**{sender_name}** (`{req['user_a']}`) 想与你绑定")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 接受", key=f"accept_{req['couple_id']}",
                             use_container_width=True, type="primary"):
                    auth_module.accept_bind(req["couple_id"])
                    st.success("绑定成功！")
                    st.rerun()
            with col2:
                if st.button("❌ 拒绝", key=f"reject_{req['couple_id']}",
                             use_container_width=True):
                    auth_module.reject_bind(req["couple_id"])
                    st.info("已拒绝。")
                    st.rerun()
        st.divider()

    # ── 情侣关系面板 ──
    st.markdown("### 💑 情侣关系")

    if not couple:
        # 未绑定：发送绑定请求
        with st.form("bind_form"):
            target_id = st.text_input(
                "输入伴侣的用户 ID",
                placeholder="usr_xxxxxxxx",
                help="让伴侣在「账户」页找到自己的 ID 并告诉你",
            )
            if st.form_submit_button("发送绑定请求", use_container_width=True, type="primary"):
                try:
                    auth_module.send_bind_request(user["user_id"], target_id.strip())
                    st.success("绑定请求已发送，等待对方确认。")
                    st.rerun()
                except auth_module.CoupleError as e:
                    st.error(str(e))

    elif couple["couple_status"] == "pending_bind":
        is_sender = couple["user_a"] == user["user_id"]
        if is_sender:
            partner = db_module.get_user_by_id(couple["user_b"])
            partner_name = partner["username"] if partner else couple["user_b"]
            st.info(f"⌛ 已向 **{partner_name}** 发出绑定请求，等待对方在「账户」页确认……")
        else:
            st.warning("👆 你收到了绑定邀请，请在上方「收到的绑定请求」区点击 **接受** 或 **拒绝**。")

    elif couple["couple_status"] == "active":
        partner_id = _partner_id()
        partner    = db_module.get_user_by_id(partner_id) if partner_id else None
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
                    auth_module.start_uncouple(user["user_id"])
                    st.warning("已进入冻结期，90 天后数据将被销毁。")
                    st.rerun()
            with col_m:
                if st.button("💔 我们双方都同意（立即销毁）",
                             use_container_width=True, type="secondary"):
                    auth_module.confirm_uncouple(user["user_id"])
                    st.error("已销毁全部数据。")
                    st.session_state["user"] = None
                    st.rerun()

    elif couple["couple_status"] == "frozen":
        ends_at = couple.get("freeze_ends_at", "")
        st.error(f"❄️ 关系处于冻结期，到期时间：**{ends_at}**，到期后数据将被自动销毁。")
        st.info("冻结期内应用为只读状态，无法上传或编辑内容。")

        # 冻结期内允许导出自己的数据
        st.markdown("---")
        st.markdown("#### 📦 导出我的数据")
        st.caption("冻结期内可导出属于自己的文件和文字记录，不包含对方数据。")
        if st.button("生成导出包", use_container_width=True):
            export_files = db_module.collect_export_files(user["user_id"])
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


# ─────────────────────────────────────────────────────────────────────────────
# 主函数
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    db_module.ensure_dirs()
    _init_state()

    user = _current_user()

    if not user:
        render_auth_page()
        return

    # 每次加载推进状态机
    db = db_module.load_db_with_tick()

    # 顶部栏
    col_title, col_user = st.columns([5, 1])
    with col_title:
        st.markdown("## 💑 OurPresent")
    with col_user:
        couple = _couple()
        if couple and couple.get("couple_status") == "active":
            partner = db_module.get_user_by_id(_partner_id())
            p_name  = partner["username"] if partner else "?"
            st.caption(f"👤 {user['username']} · 💑 {p_name}")
        else:
            st.caption(f"👤 {user['username']}")

    if _is_frozen():
        st.warning("❄️ 关系处于冻结期，当前为只读状态。")

    # 主 Tab
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗂️ 记录舱",
        "🖼️ 灵感墙",
        "📚 已归档",
        "💌 情侣空间",
        "⚙️ 账户",
    ])

    with tab1:
        render_upload_tab()
    with tab2:
        render_pending_tab(db)
    with tab3:
        render_archived_tab(db)
    with tab4:
        render_shared_tab(db)
    with tab5:
        render_account_tab(db)


if __name__ == "__main__":
    main()
