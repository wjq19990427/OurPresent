"""
可复用 UI 组件：会话状态工具、显示辅助、字段渲染、卡片、详情区、评论区。
所有函数均依赖已登录的 st.session_state["user"]。
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

from core.config import FIELD_SCHEMA, TEXT_EXTS
from backend.db_manager import (
    get_user_by_id,
    get_couple_for_user,
    _parse_dt,
)
from backend.session_manager import (
    add_comment,
    delete_comment,
    request_unlock,
    revoke_unlock,
    update_session_fields,
    move_to_final,
)
from backend.auth_manager import is_frozen, can_view_session
from utils.validators import validate_session, _is_text_session

try:
    import cv2
    from PIL import Image, ImageDraw
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False


# ── 会话状态工具 ──────────────────────────────────────────────────────────

def _current_user() -> Optional[dict]:
    return st.session_state.get("user")


def _uid() -> str:
    return _current_user()["user_id"]


def _is_frozen() -> bool:
    return is_frozen(_uid())


def _couple() -> Optional[dict]:
    return get_couple_for_user(_uid())


def _partner_id() -> Optional[str]:
    c = _couple()
    if not c or c.get("couple_status") != "active":
        return None
    return c["user_b"] if c["user_a"] == _uid() else c["user_a"]


# ── 显示辅助 ──────────────────────────────────────────────────────────────

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
    if ext in TEXT_EXTS:
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
    upload_dt = _parse_dt(session.get("upload_time", ""))
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


# ── 字段渲染（form 内）────────────────────────────────────────────────────

def _looks_like_date(s: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", s or ""))


def render_field_inputs(
    prefix: str,
    defaults: Optional[dict] = None,
    skip_keys: Optional[set] = None,
) -> dict:
    """遍历 FIELD_SCHEMA 渲染所有字段控件，必须在 with st.form(): 内调用。"""
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
                    label,
                    value=default_val if not _looks_like_date(default_val) else "",
                    placeholder=f.get("placeholder", ""),
                    help="可自由输入，如「2023年春天」",
                    key=wkey + "_free",
                )
            with sub_col2:
                try:
                    date_default = (
                        datetime.strptime(default_val, "%Y-%m-%d").date()
                        if _looks_like_date(default_val) else None
                    )
                except ValueError:
                    date_default = None
                picked = st.date_input("或选择日期", value=date_default, key=wkey + "_date")
            result[key] = free.strip() if free.strip() else (str(picked) if picked else "")
        else:
            result[key] = st.text_input(
                label, value=default_val, placeholder=f.get("placeholder", ""),
                help=f.get("help", ""), key=wkey,
            )
    return result


# ── 评论区渲染（form 外部）────────────────────────────────────────────────

def render_comments(session: dict) -> None:
    st.markdown("#### 💬 评论区")
    comments = session.get("comments", [])
    if not comments:
        st.caption("暂无评论")
    for c in comments:
        author_obj  = get_user_by_id(c.get("author", ""))
        author_name = author_obj["username"] if author_obj else c.get("author", "")
        col_t, col_del = st.columns([9, 1])
        with col_t:
            st.markdown(f"**{author_name}** · {c['created_at']}\n\n{c['text']}")
        with col_del:
            if st.button("🗑", key=f"del_cmt_{c['id']}", help="删除评论"):
                delete_comment(session["session_id"], c["id"])
                st.rerun()
    st.divider()
    cmt_key  = f"new_cmt_{session['session_id']}"
    new_text = st.text_area("写下评论……", key=cmt_key, height=80)
    if st.button("发送评论", key=f"send_cmt_{session['session_id']}"):
        if new_text.strip():
            add_comment(session["session_id"], _uid(), new_text.strip())
            del st.session_state[cmt_key]
            st.rerun()


# ── Session 卡片 ──────────────────────────────────────────────────────────

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

        missing = validate_session(session)
        if missing:
            st.warning(f"⚠ 待补充：{', '.join(missing)}", icon=None)
        else:
            st.success("✅ 信息完整", icon=None)

        btn_label = "查看/编辑" if session.get("user_id") == _uid() else "查看"
        if st.button(btn_label, key=f"sel_{state_key}_{session['session_id']}",
                     use_container_width=True):
            st.session_state[state_key] = session["session_id"]
            st.rerun()


# ── Session 详情区 ────────────────────────────────────────────────────────

def render_detail(session: dict, mode: str, read_only: bool = False) -> None:
    """
    mode: "pending" | "final" | "shared"
    read_only: 冻结期或查看对方共享内容时为 True
    """
    is_mine   = session.get("user_id") == _uid()
    is_text_s = _is_text_session(session)
    skip_keys = {"description"} if is_text_s else set()

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
            elif ext in TEXT_EXTS and fp.exists():
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
                request_unlock(session["session_id"])
                st.success("已申请，满 90 天后对方可见。")
                st.rerun()
        elif vis == "pending_unlock":
            if st.button("↩️ 撤回共享申请", key=f"revoke_{session['session_id']}"):
                revoke_unlock(session["session_id"])
                st.info("已撤回，记录恢复为私密状态。")
                st.rerun()

    if is_text_s:
        st.info("📝 纯文字记录：描述字段由内容自动填充，不可手动修改。")

    st.markdown("---")

    if read_only:
        for f in FIELD_SCHEMA:
            if f["key"] in skip_keys:
                continue
            val = session.get(f["key"], "")
            if val:
                st.markdown(f"**{f['label']}**：{val}")
    else:
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
                    update_session_fields(session["session_id"], new_vals)
                    st.success("已保存")
                    saved = True

            if mode == "pending":
                with col_archive:
                    if st.form_submit_button("✅ 完成并归档", use_container_width=True,
                                             type="primary"):
                        update_session_fields(session["session_id"], new_vals)
                        missing = validate_session({**session, **new_vals})
                        if missing:
                            st.error(f"请先填写：{', '.join(missing)}")
                        else:
                            move_to_final(session["session_id"])
                            st.session_state["pending_selected"] = None
                            st.success("已归档！")
                            saved = True

            with col_cancel:
                if st.form_submit_button("取消"):
                    st.session_state[f"{mode}_selected"] = None
                    st.rerun()

            if saved:
                st.rerun()

    render_comments(session)
