"""
Tab 1 - upload flow.
"""

from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from backend.application.sessions import save_session_final, save_session_pending, validate_session
from backend.config.settings import TEXT_EXTS
from backend.domain.models import SessionRecord
from frontend.streamlit_app.components import _couple, _is_frozen, _uid, render_field_inputs


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


def render_upload_tab() -> None:
    if _is_frozen():
        st.warning("⚠️ 当前处于冻结期，应用为只读状态，无法上传新内容。")
        return

    couple = _couple()
    couple_id = couple.couple_id if couple and couple.couple_status == "active" else None

    mode = st.radio(
        "上传方式",
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
            all_text = all(Path(file_obj.name).suffix.lower() in TEXT_EXTS for file_obj in files)
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
            st.info(
                f"📝 描述已自动填充：{preview}{suffix}"
            )

        defaults = _validation_record(
            _uid(), couple_id, source_type, {"description": auto_description}
        )
        field_vals = render_field_inputs("upload", defaults=defaults, skip_keys=skip)
        if auto_description:
            field_vals["description"] = auto_description

        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("✅ 完成并归档", use_container_width=True, type="primary"):
                draft = _validation_record(_uid(), couple_id, source_type, field_vals)
                missing = validate_session(draft)
                if missing:
                    st.error(f"请先填写：{', '.join(missing)}")
                else:
                    save_session_final(_uid(), couple_id, file_data_list, source_type, field_vals)
                    st.session_state["upload_key"] += 1
                    st.success("已归档！")
                    st.rerun()
        with col2:
            if st.form_submit_button("📦 暂存到待处理", use_container_width=True):
                save_session_pending(_uid(), couple_id, file_data_list, source_type, field_vals)
                st.session_state["upload_key"] += 1
                draft = _validation_record(_uid(), couple_id, source_type, field_vals)
                missing = validate_session(draft)
                if missing:
                    st.warning(f"已暂存，待补充：{', '.join(missing)}")
                else:
                    st.success("已暂存！")
                st.rerun()
