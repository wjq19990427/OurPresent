"""
Reusable Streamlit components and helpers.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import streamlit as st

from backend.application.couples import is_frozen
from backend.application.sessions import (
    add_comment,
    delete_comment,
    is_text_session,
    move_to_final,
    request_unlock,
    revoke_unlock,
    update_session_fields,
    validate_session,
)
from backend.config.settings import FIELD_SCHEMA, TEXT_EXTS
from backend.domain.models import Couple, SessionRecord, User
from backend.infrastructure.database.couples_repo import get_couple_for_user
from backend.infrastructure.database.db import parse_dt
from backend.infrastructure.database.users_repo import get_user_by_id
from backend.infrastructure.media import pil_to_png_bytes, video_thumbnail

_UNLOCK_PRESETS = (
    "立即",
    "1 天后",
    "3 天后",
    "1 周后",
    "1 个月后",
    "90 天后",
    "自定义日期",
)

_UNLOCK_PRESET_DAYS = {
    "1 天后": 1,
    "3 天后": 3,
    "1 周后": 7,
    "1 个月后": 30,
    "90 天后": 90,
}


def _current_user() -> Optional[User]:
    return st.session_state.get("user")


def _uid() -> str:
    return _current_user().user_id


def _is_frozen() -> bool:
    return is_frozen(_uid())


def _couple() -> Optional[Couple]:
    return get_couple_for_user(_uid())


def _partner_id() -> Optional[str]:
    couple = _couple()
    if not couple or couple.couple_status != "active":
        return None
    return couple.user_b if couple.user_a == _uid() else couple.user_a


def _session_thumb(session: SessionRecord):
    files = session.files
    if not files:
        text = session.description
        return None, (text[:80] + "…") if len(text) > 80 else text
    first = Path(files[0]["path"])
    ext = first.suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        try:
            from PIL import Image

            return Image.open(first), ""
        except Exception:
            return None, "图片读取失败"
    if ext == ".mp4":
        return video_thumbnail(first)
    if ext in TEXT_EXTS:
        try:
            preview = first.read_text(encoding="utf-8", errors="ignore")[:80]
            return None, preview
        except Exception:
            return None, "文本读取失败"
    return None, f"📎 {files[0]['original_name']}"


def _days_until_unlock(session: SessionRecord) -> int:
    unlock_dt = parse_dt(session.unlock_at or "")
    if not unlock_dt:
        return 0
    remaining = unlock_dt - datetime.now()
    return max(0, remaining.days + (1 if remaining.seconds else 0))


def _unlock_at_for_choice(
    choice: str,
    custom_date: date | None = None,
    anchor: datetime | None = None,
) -> str:
    anchor = anchor or datetime.now()
    if choice == "立即":
        return anchor.strftime("%Y-%m-%d %H:%M:%S")
    if choice == "自定义日期":
        picked = custom_date or anchor.date()
        if picked <= anchor.date():
            return anchor.strftime("%Y-%m-%d %H:%M:%S")
        unlock_dt = datetime.combine(picked, anchor.time())
        return unlock_dt.strftime("%Y-%m-%d %H:%M:%S")
    days = _UNLOCK_PRESET_DAYS[choice]
    return (anchor + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def _visibility_badge(session: SessionRecord) -> str:
    visibility = session.visibility
    if visibility == "private":
        return "🔒 私密"
    if visibility == "pending_unlock":
        if not session.unlock_at:
            return "⏳ 待解锁（未设置时间）"
        days = _days_until_unlock(session)
        return f"⏳ 待解锁（还需 {days} 天）"
    return "✅ 已共享"


def _looks_like_date(value: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", value or ""))


def render_field_inputs(
    prefix: str,
    defaults: Optional[SessionRecord] = None,
    skip_keys: Optional[set] = None,
) -> dict:
    skip_keys = skip_keys or set()
    result = {}
    for field in FIELD_SCHEMA:
        key = field["key"]
        if key in skip_keys:
            result[key] = getattr(defaults, key, "") if defaults else ""
            continue
        label = field["label"] + (" *" if field["required"] else "")
        default_val = getattr(defaults, key, "") if defaults else ""
        widget_key = f"{prefix}_{key}"

        if field["type"] == "textarea":
            result[key] = st.text_area(
                label,
                value=default_val,
                placeholder=field.get("placeholder", ""),
                help=field.get("help", ""),
                key=widget_key,
            )
        elif field["type"] == "date_or_text":
            sub_col1, sub_col2 = st.columns([1, 1])
            with sub_col1:
                free = st.text_input(
                    label,
                    value=default_val if not _looks_like_date(default_val) else "",
                    placeholder=field.get("placeholder", ""),
                    help="可自由输入，如「2023年春天」",
                    key=widget_key + "_free",
                )
            with sub_col2:
                try:
                    date_default = (
                        datetime.strptime(default_val, "%Y-%m-%d").date()
                        if _looks_like_date(default_val)
                        else None
                    )
                except ValueError:
                    date_default = None
                picked = st.date_input("或选择日期", value=date_default, key=widget_key + "_date")
            result[key] = free.strip() if free.strip() else (str(picked) if picked else "")
        else:
            result[key] = st.text_input(
                label,
                value=default_val,
                placeholder=field.get("placeholder", ""),
                help=field.get("help", ""),
                key=widget_key,
            )
    return result


def _with_field_values(session: SessionRecord, values: dict) -> SessionRecord:
    valid_keys = {field["key"] for field in FIELD_SCHEMA}
    updates = {key: value for key, value in values.items() if key in valid_keys}
    return replace(session, **updates)


def render_comments(session: SessionRecord) -> None:
    st.markdown("#### 💬 评论区")
    comments = session.comments
    if not comments:
        st.caption("暂无评论")
    for comment in comments:
        author_obj = get_user_by_id(comment.get("author", ""))
        author_name = author_obj.username if author_obj else comment.get("author", "")
        col_text, col_del = st.columns([9, 1])
        with col_text:
            st.markdown(f"**{author_name}** · {comment['created_at']}\n\n{comment['text']}")
        with col_del:
            if st.button("🗑", key=f"del_cmt_{comment['id']}", help="删除评论"):
                delete_comment(session.session_id, comment["id"])
                st.rerun()
    st.divider()
    comment_key = f"new_cmt_{session.session_id}"
    new_text = st.text_area("写下评论……", key=comment_key, height=80)
    if st.button("发送评论", key=f"send_cmt_{session.session_id}"):
        if new_text.strip():
            add_comment(session.session_id, _uid(), new_text.strip())
            del st.session_state[comment_key]
            st.rerun()


def render_card(col, session: SessionRecord, state_key: str) -> None:
    with col:
        thumb, label = _session_thumb(session)
        if thumb:
            st.image(pil_to_png_bytes(thumb), use_container_width=True)
        else:
            st.markdown(f"```\n{label[:120]}\n```")

        n_files = len(session.files)
        n_comments = len(session.comments)
        st.caption(f"📎 {n_files}  💬 {n_comments}  ·  {session.upload_time[:10]}")
        st.caption(_visibility_badge(session))

        missing = validate_session(session)
        if missing:
            st.warning(f"⚠ 待补充：{', '.join(missing)}", icon=None)
        else:
            st.success("✅ 信息完整", icon=None)

        button_label = "查看/编辑" if session.user_id == _uid() else "查看"
        if st.button(
            button_label, key=f"sel_{state_key}_{session.session_id}", use_container_width=True
        ):
            st.session_state[state_key] = session.session_id
            st.rerun()


def render_detail(session: SessionRecord, mode: str, read_only: bool = False) -> None:
    is_mine = session.user_id == _uid()
    is_text = is_text_session(session)
    skip_keys = {"description"} if is_text else set()

    with st.expander("📁 文件预览", expanded=False):
        for file_record in session.files:
            file_path = Path(file_record["path"])
            ext = file_path.suffix.lower()
            st.markdown(f"**{file_record['original_name']}**")
            if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"} and file_path.exists():
                st.image(str(file_path), use_container_width=True)
            elif ext == ".mp4" and file_path.exists():
                st.video(str(file_path))
            elif ext in TEXT_EXTS and file_path.exists():
                st.text(file_path.read_text(encoding="utf-8", errors="ignore")[:2000])
            else:
                st.caption(f"📎 {file_record['original_name']} — 不支持预览")

    if mode == "final" and session.edit_history:
        with st.expander("🕐 编辑历史", expanded=False):
            for entry in reversed(session.edit_history):
                st.markdown(f"**{entry['edited_at']}**")
                for key, value in entry["changes"].items():
                    label = next(
                        (field["label"] for field in FIELD_SCHEMA if field["key"] == key), key
                    )
                    st.markdown(f"- {label}：`{value['from']}` → `{value['to']}`")

    if is_mine and not read_only:
        visibility = session.visibility
        st.markdown("---")
        st.markdown(f"**隐私状态**：{_visibility_badge(session)}")
        if visibility == "private":
            unlock_choice = st.selectbox(
                "对方何时可见",
                _UNLOCK_PRESETS,
                index=_UNLOCK_PRESETS.index("1 周后"),
                key=f"unlock_choice_{session.session_id}",
            )
            custom_unlock_date = None
            if unlock_choice == "自定义日期":
                custom_unlock_date = st.date_input(
                    "选择开放日期",
                    value=datetime.now().date(),
                    min_value=datetime.now().date(),
                    key=f"unlock_custom_date_{session.session_id}",
                )
            if st.button("📤 申请共享给对方", key=f"unlock_{session.session_id}"):
                unlock_at = _unlock_at_for_choice(unlock_choice, custom_unlock_date)
                request_unlock(session.session_id, unlock_at)
                if parse_dt(unlock_at) and parse_dt(unlock_at) <= datetime.now():
                    st.success("已共享，对方现在可见。")
                else:
                    st.success(f"已申请，对方将在 {unlock_at} 后可见。")
                st.rerun()
        elif visibility == "pending_unlock":
            if st.button("↩️ 撤回共享申请", key=f"revoke_{session.session_id}"):
                revoke_unlock(session.session_id)
                st.info("已撤回，记录恢复为私密状态。")
                st.rerun()

    if is_text:
        st.info("📝 纯文字记录：描述字段由内容自动填充，不可手动修改。")

    st.markdown("---")

    if read_only:
        for field in FIELD_SCHEMA:
            if field["key"] in skip_keys:
                continue
            value = getattr(session, field["key"], "")
            if value:
                st.markdown(f"**{field['label']}**：{value}")
    else:
        with st.form(key=f"detail_form_{session.session_id}_{mode}"):
            new_values = render_field_inputs(
                prefix=f"edit_{session.session_id}",
                defaults=session,
                skip_keys=skip_keys,
            )

            col_save, col_archive, col_cancel = st.columns([2, 2, 1])
            saved = False

            with col_save:
                if st.form_submit_button("💾 保存更改", use_container_width=True):
                    update_session_fields(session.session_id, new_values)
                    st.success("已保存")
                    saved = True

            if mode == "pending":
                with col_archive:
                    if st.form_submit_button(
                        "✅ 完成并归档", use_container_width=True, type="primary"
                    ):
                        update_session_fields(session.session_id, new_values)
                        missing = validate_session(_with_field_values(session, new_values))
                        if missing:
                            st.error(f"请先填写：{', '.join(missing)}")
                        else:
                            move_to_final(session.session_id)
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
