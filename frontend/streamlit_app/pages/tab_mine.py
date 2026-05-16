"""Mine tab - new record entry and personal timeline."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import streamlit as st

from backend.application.sessions import save_session_final, save_session_pending, validate_session
from backend.config.settings import TEXT_EXTS
from backend.domain.models import SessionRecord
from backend.infrastructure.database.db import parse_dt
from backend.infrastructure.database.sessions_repo import (
    list_sessions_for_couple,
    list_sessions_for_user,
)
from frontend.streamlit_app.components import (
    _couple,
    _is_frozen,
    _uid,
    render_card,
    render_detail,
    render_field_inputs,
)


def _can_create_records(couple) -> bool:
    return bool(couple and couple.couple_status == "active")


def _recording_gate_message(couple) -> str | None:
    if not couple:
        return "先去「设置」里绑定伴侣。关系连上后，这里就会开始留下只属于你的记录。"
    if couple.couple_status == "pending_bind":
        return "等绑定确认后，这里会打开写记录和共享。"
    return None


def _pending_unlock_sort_key(session: SessionRecord) -> tuple[str, str]:
    return (session.unlock_at or "9999-12-31 23:59:59", session.upload_time)


def _next_unlock_label(sessions: list[SessionRecord]) -> str | None:
    if not sessions:
        return None
    unlock_dt = parse_dt(sessions[0].unlock_at or "")
    if not unlock_dt:
        return "最快开放时间待定"
    remaining = unlock_dt - datetime.now()
    if remaining.total_seconds() <= 0:
        return "最快即将开放"
    days = remaining.days
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    if days > 0:
        return f"最快 {days + (1 if remaining.seconds else 0)} 天后开放"
    if hours > 0:
        return f"最快 {hours} 小时后开放"
    return f"最快 {max(1, minutes)} 分钟后开放"


def _should_show_first_record_guide(couple, couple_sessions: list[SessionRecord]) -> bool:
    return bool(couple and couple.couple_status == "active" and not couple_sessions)


def _render_group(
    title: str,
    sessions: list[SessionRecord],
    *,
    summary: str | None = None,
    can_create_records: bool,
) -> None:
    if not sessions:
        return

    st.markdown(f"#### {title} · {len(sessions)} 条")
    if summary:
        st.caption(summary)

    selected_id = st.session_state.get("mine_selected")
    cols = st.columns(3)
    for index, session in enumerate(sessions):
        target_col = cols[index % 3]
        render_card(target_col, session, "mine_selected")
        if selected_id == session.session_id:
            with target_col:
                mode = "pending" if session.status == "pending" else "final"
                render_detail(
                    session,
                    mode=mode,
                    read_only=_is_frozen() or not can_create_records,
                    selected_state_key="mine_selected",
                    show_comments=False,
                    show_file_preview=False,
                )


def _validation_record(
    user_id: str,
    couple_id: str | None,
    source_type: str,
    field_values: dict,
) -> SessionRecord:
    session = SessionRecord(
        session_id="upload_preview",
        user_id=user_id,
        couple_id=couple_id,
        status="pending",
        visibility="private",
        unlock_requested_at=None,
        unlock_at=None,
        shared_at=None,
        upload_time="",
        archive_time="",
        is_complete=False,
        source_type=source_type,
    )
    for key, value in field_values.items():
        if hasattr(session, key):
            setattr(session, key, value)
    return session


def _render_new_record_entry(*, has_sessions: bool) -> None:
    if _is_frozen():
        st.info("这段时间先不写新记录。等关系回到正常状态后，这里会重新打开。")
        return

    if not has_sessions:
        st.markdown("### 写下新的记录")
        st.caption("先留下这一刻。等它完成后，再决定什么时候让对方看见。")

    with st.expander("✍️ 写新记录", expanded=not has_sessions):
        couple = _couple()
        couple_id = couple.couple_id if couple and couple.couple_status == "active" else None

        mode = st.radio(
            "记录方式",
            ["上传文件", "粘贴文字"],
            horizontal=True,
            key=f"upload_mode_{st.session_state['upload_key']}",
        )

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
                for file_obj in files:
                    file_data_list.append((file_obj.read(), file_obj.name))
                all_text = all(
                    Path(file_obj.name).suffix.lower() in TEXT_EXTS for file_obj in files
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
                "在此粘贴文字", height=200, key=f"paste_{st.session_state['upload_key']}"
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
                preview = auto_description[:60]
                suffix = "…" if len(auto_description) > 60 else ""
                st.info(f"📝 描述已自动填充：{preview}{suffix}")

            defaults = _validation_record(
                _uid(), couple_id, source_type, {"description": auto_description}
            )
            field_vals = render_field_inputs("upload", defaults=defaults, skip_keys=skip)
            if auto_description:
                field_vals["description"] = auto_description

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("✅ 完成", width="stretch", type="primary"):
                    draft = _validation_record(_uid(), couple_id, source_type, field_vals)
                    missing = validate_session(draft)
                    if missing:
                        st.error(f"请先填写：{', '.join(missing)}")
                    else:
                        save_session_final(
                            _uid(), couple_id, file_data_list, source_type, field_vals
                        )
                        st.session_state["upload_key"] += 1
                        st.success("已完成！")
                        st.rerun()
            with col2:
                if st.form_submit_button("📦 存为草稿", width="stretch"):
                    save_session_pending(_uid(), couple_id, file_data_list, source_type, field_vals)
                    st.session_state["upload_key"] += 1
                    draft = _validation_record(_uid(), couple_id, source_type, field_vals)
                    missing = validate_session(draft)
                    if missing:
                        st.warning(f"已保存，待补充：{', '.join(missing)}")
                    else:
                        st.success("已保存！")
                    st.rerun()


def render_mine_tab(db: dict) -> None:
    couple = _couple()
    can_create_records = _can_create_records(couple)
    couple_sessions = list_sessions_for_couple(couple.couple_id) if couple else []
    sessions = [
        session
        for session in list_sessions_for_user(_uid())
        if session.visibility != "shared"
    ]
    waiting_sessions = sorted(
        [session for session in sessions if session.visibility == "pending_unlock"],
        key=_pending_unlock_sort_key,
    )
    private_sessions = sorted(
        [session for session in sessions if session.visibility != "pending_unlock"],
        key=lambda session: session.upload_time,
        reverse=True,
    )

    st.caption("这里只显示你自己写的、还没开放的记录。已经共享的会去「我们」。")

    if _should_show_first_record_guide(couple, couple_sessions):
        with st.container(border=True):
            st.markdown("#### 你们绑定了，先写下第一条记录")
            st.caption("它会先留在你这里，等你决定什么时候让对方看见。")

    if _is_frozen():
        _render_new_record_entry(has_sessions=bool(sessions))
    elif can_create_records:
        _render_new_record_entry(has_sessions=bool(sessions))
    else:
        gate_message = _recording_gate_message(couple)
        if gate_message:
            st.info(gate_message)
    st.divider()

    if not sessions:
        if can_create_records:
            st.info("这里暂时没有还没开放的记录。写下新的内容后，它会先留在这里。")
        return

    _render_group(
        "等待开放",
        waiting_sessions,
        summary=_next_unlock_label(waiting_sessions),
        can_create_records=can_create_records,
    )
    if waiting_sessions and private_sessions:
        st.divider()
    _render_group(
        "私密记录",
        private_sessions,
        can_create_records=can_create_records,
    )

    selected_id = st.session_state.get("mine_selected")
    if selected_id and not any(item.session_id == selected_id for item in sessions):
        st.session_state["mine_selected"] = None
