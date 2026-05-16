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

from backend.application.couples import (
    CoupleError,
    confirm_cancel_uncouple,
    confirm_destroy_uncouple,
    is_frozen,
    reject_cancel_uncouple,
    reject_destroy_uncouple,
    request_cancel_uncouple,
    request_destroy_uncouple,
    withdraw_cancel_request,
    withdraw_destroy_request,
)
from backend.application.sessions import (
    add_comment,
    append_to_session,
    delete_comment,
    delete_session,
    is_text_session,
    move_to_final,
    request_unlock,
    reschedule_unlock,
    revoke_unlock,
    unlock_now,
    update_session_fields,
    validate_session,
)
from backend.config.settings import FIELD_SCHEMA, TEXT_EXTS
from backend.domain.models import Couple, Report, SessionRecord, User
from backend.infrastructure.database.couples_repo import get_couple_for_user
from backend.infrastructure.database.db import parse_dt
from backend.infrastructure.database.users_repo import get_user_by_id
from backend.infrastructure.media import pil_to_png_bytes

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

_APPENDABLE_TEXT_FIELDS = tuple(
    field["key"] for field in FIELD_SCHEMA if field.get("type") == "textarea"
)

_UPLOAD_FIELD_ORDER = ("description", "feeling", "reason", "content_time")


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
        return None, f"🎞 {files[0]['original_name']}"
    if ext in TEXT_EXTS:
        try:
            preview = first.read_text(encoding="utf-8", errors="ignore")[:80]
            return None, preview
        except Exception:
            return None, "文本读取失败"
    return None, f"📎 {files[0]['original_name']}"


def _render_session_preview(session: SessionRecord) -> None:
    files = session.files
    if not files:
        text = session.description
        preview = (text[:80] + "…") if len(text) > 80 else text
        st.markdown(f"```\n{preview}\n```")
        return

    first = Path(files[0]["path"])
    ext = first.suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        thumb, label = _session_thumb(session)
        if thumb:
            st.image(pil_to_png_bytes(thumb), width="stretch")
            return
        st.markdown(f"```\n{label[:120]}\n```")
        return
    if ext == ".mp4" and first.exists():
        st.video(str(first))
        return
    if ext in TEXT_EXTS:
        try:
            preview = first.read_text(encoding="utf-8", errors="ignore")[:80]
            st.markdown(f"```\n{preview}\n```")
            return
        except Exception:
            st.markdown("```\n文本读取失败\n```")
            return
    st.markdown(f"```\n📎 {files[0]['original_name']}\n```")


def _days_until_unlock(session: SessionRecord) -> int:
    unlock_dt = parse_dt(session.unlock_at or "")
    if not unlock_dt:
        return 0
    remaining = unlock_dt - datetime.now()
    return max(0, remaining.days + (1 if remaining.seconds else 0))


def _time_until_unlock_text(session: SessionRecord) -> str:
    unlock_dt = parse_dt(session.unlock_at or "")
    if not unlock_dt:
        return "开放时间待定"
    remaining = unlock_dt - datetime.now()
    if remaining.total_seconds() <= 0:
        return "即将开放"
    days = remaining.days
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    if days > 0:
        return f"还要 {days + (1 if remaining.seconds else 0)} 天"
    if hours > 0:
        return f"还要 {hours} 小时"
    return f"还要 {max(1, minutes)} 分钟"


def _freeze_days_left(couple: Couple) -> int:
    freeze_ends = parse_dt(couple.freeze_ends_at or "")
    if not freeze_ends:
        return 0
    remaining = freeze_ends - datetime.now()
    if remaining.total_seconds() <= 0:
        return 0
    return max(1, remaining.days + (1 if remaining.seconds else 0))


def _set_frozen_notice(level: str, message: str) -> None:
    st.session_state["frozen_notice"] = {"level": level, "message": message}


def _render_frozen_notice() -> None:
    notice = st.session_state.pop("frozen_notice", None)
    if not notice:
        return
    getattr(st, notice["level"], st.info)(notice["message"])


def _run_frozen_action(action: str) -> None:
    user_id = _uid()
    try:
        if action == "request":
            request_cancel_uncouple(user_id)
            _set_frozen_notice("success", "已把想回到正常状态的想法告诉对方，等对方回应。")
        elif action == "confirm":
            confirm_cancel_uncouple(user_id)
            _set_frozen_notice("success", "你们已经回到正常状态，之前留下的内容都还在。")
        elif action == "reject":
            reject_cancel_uncouple(user_id)
            _set_frozen_notice("info", "已保持冻结期不变；如果之后想再谈，还可以重新发起。")
        elif action == "withdraw":
            withdraw_cancel_request(user_id)
            _set_frozen_notice("info", "已收回这次撤回请求，关系仍停在冻结期。")
        elif action == "request_destroy":
            request_destroy_uncouple(user_id)
            _set_frozen_notice(
                "warning",
                "已发出现在分手申请。只有对方点头后，数据才会被永久销毁。",
            )
        elif action == "confirm_destroy":
            confirm_destroy_uncouple(user_id)
            st.session_state["user"] = get_user_by_id(user_id)
            st.session_state["farewell_state"] = {"reason": "destroy_now"}
        elif action == "reject_destroy":
            reject_destroy_uncouple(user_id)
            _set_frozen_notice("info", "已先不走现在分手这一步，关系仍停在冻结期。")
        elif action == "withdraw_destroy":
            withdraw_destroy_request(user_id)
            _set_frozen_notice("info", "已收回这次现在分手申请，关系仍停在冻结期。")
    except CoupleError as exc:
        _set_frozen_notice("error", str(exc))
    st.rerun()


def render_frozen_status_banner(*, scope: str) -> None:
    couple = _couple()
    if not couple or couple.couple_status != "frozen":
        return

    pending_key = f"{scope}_pending_frozen_action"
    initiated_by_me = couple.uncouple_initiated_by == _uid()
    cancel_requested_by = couple.cancel_uncouple_requested_by
    cancel_requested_by_me = cancel_requested_by == _uid()
    destroy_requested_by = couple.destroy_uncouple_requested_by
    destroy_requested_by_me = destroy_requested_by == _uid()
    days_left = _freeze_days_left(couple)
    remaining_text = f"还有 {days_left} 天" if days_left else "快到期了"

    _render_frozen_notice()

    with st.container(border=True):
        if initiated_by_me:
            st.markdown(f"**你按下了冷静键。你们处于冻结期，{remaining_text}。**")
        else:
            st.markdown(f"**对方按下了冷静键。你们处于冻结期，{remaining_text}。**")
        st.caption("这段时间里先停一停。新的记录和编辑会先暂停；到期后，数据会自动销毁。")

        if cancel_requested_by:
            if cancel_requested_by_me:
                st.info("已发出撤回冻结请求，正在等对方回应。")
                if st.button(
                    "撤回我的请求",
                    key=f"{scope}_withdraw_cancel_uncouple",
                    width="stretch",
                ):
                    st.session_state[pending_key] = "withdraw"
                    st.rerun()
            else:
                st.info("对方想撤回冻结期，回到正常状态。")
                agree_col, reject_col = st.columns(2)
                with agree_col:
                    if st.button(
                        "同意撤回",
                        key=f"{scope}_confirm_cancel_uncouple",
                        width="stretch",
                    ):
                        st.session_state[pending_key] = "confirm"
                        st.rerun()
                with reject_col:
                    if st.button(
                        "拒绝撤回",
                        key=f"{scope}_reject_cancel_uncouple",
                        width="stretch",
                    ):
                        st.session_state[pending_key] = "reject"
                        st.rerun()
        elif destroy_requested_by:
            if destroy_requested_by_me:
                st.warning("已发出现在分手申请。只有对方同意后，数据才会被永久销毁。")
                if st.button(
                    "撤回我的现在分手申请",
                    key=f"{scope}_withdraw_destroy_uncouple",
                    width="stretch",
                ):
                    st.session_state[pending_key] = "withdraw_destroy"
                    st.rerun()
            else:
                st.warning("对方想现在分手。如果你同意，记录、评论和周报都会一起永久消失。")
                agree_col, reject_col = st.columns(2)
                with agree_col:
                    if st.button(
                        "同意现在分手",
                        key=f"{scope}_confirm_destroy_uncouple",
                        width="stretch",
                    ):
                        st.session_state[pending_key] = "confirm_destroy"
                        st.rerun()
                with reject_col:
                    if st.button(
                        "拒绝现在分手",
                        key=f"{scope}_reject_destroy_uncouple",
                        width="stretch",
                    ):
                        st.session_state[pending_key] = "reject_destroy"
                        st.rerun()
        else:
            st.info("如果想回到正常状态，或想现在就结束这段关系，都需要先把想法发给对方。")
            request_col, destroy_col = st.columns(2)
            with request_col:
                if st.button("撤回冻结", key=f"{scope}_request_cancel_uncouple", width="stretch"):
                    st.session_state[pending_key] = "request"
                    st.rerun()
            with destroy_col:
                if st.button("现在分手", key=f"{scope}_request_destroy_uncouple", width="stretch"):
                    st.session_state[pending_key] = "request_destroy"
                    st.rerun()

        pending_action = st.session_state.get(pending_key)
        prompts = {
            "request": (
                "把这个想法告诉对方后，关系仍会先停在冻结期，直到对方回应。",
                "发出请求",
            ),
            "confirm": (
                "同意后，你们会回到正常状态，之前留下的记录会继续保留。",
                "同意撤回",
            ),
            "reject": (
                "拒绝后，关系继续停在冻结期。这次请求会被清掉，之后仍可以重新讨论。",
                "继续冻结",
            ),
            "withdraw": (
                "这会收回你刚才发出的撤回请求，关系仍保持冻结。",
                "撤回请求",
            ),
            "request_destroy": (
                "发出现在分手申请后，关系仍先保持冻结。只有对方同意，数据才会被永久销毁。",
                "发出申请",
            ),
            "confirm_destroy": (
                "同意后，记录、评论和周报都会一起永久销毁，之后无法恢复。",
                "确认永久销毁",
            ),
            "reject_destroy": (
                "拒绝后，这次现在分手申请会被清掉，关系继续停在冻结期。",
                "继续冻结",
            ),
            "withdraw_destroy": (
                "这会收回你刚才发出的现在分手申请，关系仍保持冻结。",
                "撤回申请",
            ),
        }
        if pending_action in prompts:
            prompt_text, confirm_label = prompts[pending_action]
            st.warning(prompt_text)
            confirm_col, cancel_col = st.columns(2)
            with confirm_col:
                if st.button(
                    confirm_label,
                    key=f"{scope}_confirm_{pending_action}",
                    width="stretch",
                    type="primary",
                ):
                    st.session_state.pop(pending_key, None)
                    _run_frozen_action(pending_action)
            with cancel_col:
                if st.button(
                    "先等等",
                    key=f"{scope}_cancel_{pending_action}",
                    width="stretch",
                ):
                    st.session_state.pop(pending_key, None)
                    st.rerun()


def _is_recently_shared(session: SessionRecord) -> bool:
    shared_dt = parse_dt(session.shared_at or "")
    if not shared_dt:
        return False
    elapsed = datetime.now() - shared_dt
    return timedelta(0) <= elapsed < timedelta(hours=24)


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
            return "等待开放（未设置时间）"
        return f"等待开放（{_time_until_unlock_text(session)}）"
    return "✅ 已共享"


def _status_badge(session: SessionRecord) -> str:
    if session.status == "pending":
        return "[草稿]"
    if session.visibility == "private":
        return "[仅自己]"
    if session.visibility == "pending_unlock":
        return f"[等待开放 · {_time_until_unlock_text(session)}]"
    return "[已分享]"


def _fields_for_prefix(prefix: str) -> list[dict]:
    if prefix != "upload":
        return FIELD_SCHEMA
    by_key = {field["key"]: field for field in FIELD_SCHEMA}
    ordered = [by_key[key] for key in _UPLOAD_FIELD_ORDER if key in by_key]
    ordered.extend(field for field in FIELD_SCHEMA if field["key"] not in _UPLOAD_FIELD_ORDER)
    return ordered


def _report_status_badge(report: Report) -> str:
    if report.status == "sparse":
        return "记录较少"
    if report.status == "ready":
        return "已生成"
    return report.status


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


def render_weekly_report(report: Report) -> None:
    st.caption(f"{report.window_start} → {report.window_end}")
    _render_report_footprint(report)
    if report.status == "sparse":
        st.info("这周共享记录较少，留些空白也好。")
        return
    _render_report_weather(report)
    _render_report_resonance(report)
    _render_report_suspense(report)


def render_report_history(reports: list[Report]) -> None:
    visible_reports = sorted(
        [report for report in reports if report.status != "failed"],
        key=lambda report: report.generated_at,
        reverse=True,
    )
    if not visible_reports:
        st.caption("还没有可查看的历史周报。")
        return

    for report in visible_reports:
        label = (
            f"{report.window_start[:10]} ~ {report.window_end[:10]} · "
            f"{_report_status_badge(report)}"
        )
        with st.expander(label, expanded=False):
            render_weekly_report(report)


def _looks_like_date(value: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", value or ""))


def _field_label(key: str) -> str:
    return next((field["label"] for field in FIELD_SCHEMA if field["key"] == key), key)


def render_field_inputs(
    prefix: str,
    defaults: Optional[SessionRecord] = None,
    skip_keys: Optional[set] = None,
) -> dict:
    skip_keys = skip_keys or set()
    result = {}
    for field in _fields_for_prefix(prefix):
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


def render_comments(session: SessionRecord, *, key_scope: str = "comments") -> None:
    st.markdown("#### 💬 评论区")
    comments = session.comments
    pending_delete_key = f"{key_scope}_pending_delete_cmt_{session.session_id}"
    if not comments:
        st.caption("暂无评论")
    for comment in comments:
        author_obj = get_user_by_id(comment.get("author", ""))
        author_name = author_obj.username if author_obj else comment.get("author", "")
        col_text, col_del = st.columns([9, 1])
        with col_text:
            st.markdown(f"**{author_name}** · {comment['created_at']}\n\n{comment['text']}")
        with col_del:
            if comment.get("author") == _uid():
                if st.button(
                    "🗑",
                    key=f"{key_scope}_del_cmt_{comment['id']}",
                    help="删除评论",
                ):
                    st.session_state[pending_delete_key] = comment["id"]
                    st.rerun()
        if st.session_state.get(pending_delete_key) == comment["id"]:
            st.warning("确认删除这条评论？删除后无法恢复。", icon="⚠️")
            confirm_col, cancel_col = st.columns(2)
            with confirm_col:
                if st.button(
                    "确认删除",
                    key=f"{key_scope}_confirm_del_cmt_{comment['id']}",
                    width="stretch",
                ):
                    delete_comment(session.session_id, comment["id"], _uid())
                    st.session_state.pop(pending_delete_key, None)
                    st.rerun()
            with cancel_col:
                if st.button(
                    "取消",
                    key=f"{key_scope}_cancel_del_cmt_{comment['id']}",
                    width="stretch",
                ):
                    st.session_state.pop(pending_delete_key, None)
                    st.rerun()
    st.divider()
    comment_key = f"{key_scope}_new_cmt_{session.session_id}"
    new_text = st.text_area("写下评论……", key=comment_key, height=80)
    if st.button("发送评论", key=f"{key_scope}_send_cmt_{session.session_id}"):
        if new_text.strip():
            add_comment(session.session_id, _uid(), new_text.strip())
            del st.session_state[comment_key]
            st.rerun()


def render_card(
    col,
    session: SessionRecord,
    state_key: str,
    author_name: str | None = None,
    *,
    author_relation: str | None = None,
    show_completion: bool = True,
    show_recently_shared: bool = False,
    button_label: str | None = None,
    show_status_badge: bool = True,
    show_description: bool = False,
) -> None:
    with col:
        if author_name:
            label = (
                f"{author_relation} · {author_name}"
                if author_relation
                else f"作者：{author_name}"
            )
            st.caption(label)
        if show_recently_shared and _is_recently_shared(session):
            st.success("新近解锁", icon=None)
        _render_session_preview(session)

        n_files = len(session.files)
        n_comments = len(session.comments)
        st.caption(f"📎 {n_files}  💬 {n_comments}  ·  {session.upload_time[:10]}")
        if show_description and session.description.strip():
            st.write(session.description.strip())
        if show_status_badge:
            st.caption(_status_badge(session))

        if show_completion:
            missing = validate_session(session)
            if missing:
                st.warning(f"⚠ 待补充：{', '.join(missing)}", icon=None)
            else:
                st.success("✅ 信息完整", icon=None)

        button_label = button_label or ("查看/编辑" if session.user_id == _uid() else "查看")
        if st.button(
            button_label, key=f"sel_{state_key}_{session.session_id}", width="stretch"
        ):
            current = st.session_state.get(state_key)
            st.session_state[state_key] = (
                None if current == session.session_id else session.session_id
            )
            st.rerun()


def render_detail(
    session: SessionRecord,
    mode: str,
    read_only: bool = False,
    *,
    selected_state_key: str,
    show_comments: bool | None = None,
    show_file_preview: bool = True,
) -> None:
    is_mine = session.user_id == _uid()
    is_text = is_text_session(session)
    skip_keys = {"description"} if is_text else set()

    if show_file_preview:
        with st.expander("📁 文件预览", expanded=False):
            for file_record in session.files:
                file_path = Path(file_record["path"])
                ext = file_path.suffix.lower()
                st.markdown(f"**{file_record['original_name']}**")
                if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"} and file_path.exists():
                    st.image(str(file_path), width="stretch")
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
        pending_delete_key = f"pending_delete_session_{session.session_id}"
        visibility = session.visibility
        st.markdown("---")
        st.markdown(f"**隐私状态**：{_visibility_badge(session)}")
        if visibility == "private":
            st.caption("默认先等一个月，让这份记录保留一点时间的重量；也可以改成立即或更久。")
            unlock_choice = st.selectbox(
                "对方何时可见",
                _UNLOCK_PRESETS,
                index=_UNLOCK_PRESETS.index("1 个月后"),
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
            st.caption(f"当前计划开放时间：{session.unlock_at or '未设置'}")

            with st.expander("追加内容", expanded=False):
                append_options = {
                    key: _field_label(key)
                    for key in _APPENDABLE_TEXT_FIELDS
                    if key not in skip_keys
                }
                if append_options:
                    append_field = st.selectbox(
                        "追加到字段",
                        list(append_options),
                        format_func=lambda key: append_options[key],
                        key=f"append_field_{session.session_id}",
                    )
                    append_text = st.text_area(
                        "追加内容",
                        key=f"append_text_{session.session_id}",
                        height=120,
                    )
                    if st.button("追加", key=f"append_btn_{session.session_id}"):
                        if append_text.strip():
                            append_to_session(session.session_id, append_field, append_text)
                            st.success("已追加，原文已保留。")
                            st.rerun()
                        else:
                            st.warning("请先写下要追加的内容。")

            with st.expander("修改开放时间", expanded=False):
                new_unlock_choice = st.selectbox(
                    "新的开放时间",
                    _UNLOCK_PRESETS,
                    index=_UNLOCK_PRESETS.index("1 个月后"),
                    key=f"reschedule_choice_{session.session_id}",
                )
                new_custom_unlock_date = None
                if new_unlock_choice == "自定义日期":
                    new_custom_unlock_date = st.date_input(
                        "选择新的开放日期",
                        value=datetime.now().date(),
                        min_value=datetime.now().date(),
                        key=f"reschedule_custom_date_{session.session_id}",
                    )
                confirm_reschedule = st.checkbox(
                    "我确认：这会改变伴侣看见这条记录的时间",
                    key=f"confirm_reschedule_{session.session_id}",
                )
                if st.button("修改时间", key=f"reschedule_{session.session_id}"):
                    if not confirm_reschedule:
                        st.warning("请先勾选确认。")
                    else:
                        new_unlock_at = _unlock_at_for_choice(
                            new_unlock_choice, new_custom_unlock_date
                        )
                        reschedule_unlock(session.session_id, new_unlock_at)
                        if parse_dt(new_unlock_at) and parse_dt(new_unlock_at) <= datetime.now():
                            st.success("已立即共享，对方现在可见。")
                        else:
                            st.success(f"已修改，对方将在 {new_unlock_at} 后可见。")
                        st.rerun()

            confirm_unlock_now = st.checkbox(
                "我确认：这会改变伴侣看见这条记录的时间",
                key=f"confirm_unlock_now_{session.session_id}",
            )
            if st.button("立即解锁", key=f"unlock_now_{session.session_id}"):
                if not confirm_unlock_now:
                    st.warning("请先勾选确认。")
                else:
                    unlock_now(session.session_id)
                    st.success("已共享，对方现在可见。")
                    st.rerun()

            if st.button("↩️ 撤回共享申请", key=f"revoke_{session.session_id}"):
                revoke_unlock(session.session_id)
                st.info("已撤回，记录恢复为私密状态。")
                st.rerun()

        st.markdown("---")
        if st.button("🗑 删除这条记录", key=f"delete_session_{session.session_id}", width="stretch"):
            st.session_state[pending_delete_key] = True
            st.rerun()
        if st.session_state.get(pending_delete_key):
            st.warning("确认删除这条记录？相关文件和内容会一起消失，之后无法恢复。", icon="⚠️")
            confirm_col, cancel_col = st.columns(2)
            with confirm_col:
                if st.button(
                    "确认删除",
                    key=f"confirm_delete_session_{session.session_id}",
                    width="stretch",
                ):
                    delete_session(session.session_id, _uid())
                    st.session_state.pop(pending_delete_key, None)
                    st.session_state[selected_state_key] = None
                    st.rerun()
            with cancel_col:
                if st.button(
                    "取消",
                    key=f"cancel_delete_session_{session.session_id}",
                    width="stretch",
                ):
                    st.session_state.pop(pending_delete_key, None)
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
                if st.form_submit_button("💾 保存更改", width="stretch"):
                    update_session_fields(session.session_id, new_values)
                    st.success("已保存")
                    saved = True

            if mode == "pending":
                with col_archive:
                    if st.form_submit_button(
                        "✅ 完成", width="stretch", type="primary"
                    ):
                        update_session_fields(session.session_id, new_values)
                        missing = validate_session(_with_field_values(session, new_values))
                        if missing:
                            st.error(f"请先填写：{', '.join(missing)}")
                        else:
                            move_to_final(session.session_id)
                            st.session_state[selected_state_key] = None
                            st.success("已完成！")
                            saved = True

            with col_cancel:
                if st.form_submit_button("取消"):
                    st.session_state[selected_state_key] = None
                    st.rerun()

            if saved:
                st.rerun()

    if show_comments is None:
        show_comments = session.visibility != "pending_unlock" and (
            session.visibility == "shared" or is_mine
        )
    if show_comments:
        render_comments(session, key_scope=selected_state_key)
