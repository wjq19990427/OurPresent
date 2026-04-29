"""
Tab 1 — 🗂️ 记录舱（上传）
"""

from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from backend.db_manager import load_db
from backend.session_manager import save_session_pending, save_session_final
from utils.validators import validate_session
from core.config import TEXT_EXTS
from frontend.components import (
    _current_user, _uid, _is_frozen, _couple, render_field_inputs,
)


def render_upload_tab() -> None:
    if _is_frozen():
        st.warning("⚠️ 当前处于冻结期，应用为只读状态，无法上传新内容。")
        return

    couple    = _couple()
    couple_id = couple["couple_id"] if couple and couple.get("couple_status") == "active" else None

    mode = st.radio(
        "上传方式", ["上传文件", "粘贴文字"], horizontal=True,
        key=f"upload_mode_{st.session_state['upload_key']}",
    )

    file_data_list: list[tuple[bytes, str]] = []
    source_type      = "file"
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
            all_text = all(Path(f.name).suffix.lower() in TEXT_EXTS for f in files)
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
            file_data_list  = [(pasted.encode("utf-8"), safe_name)]
            auto_description = pasted.strip()

    if not file_data_list:
        st.info("请先选择文件或粘贴文字。")
        return

    st.divider()
    with st.form(key=f"upload_form_{st.session_state['upload_key']}"):
        st.markdown("**填写信息**")
        skip = {"description"} if auto_description else set()
        if auto_description:
            st.info(
                f"📝 描述已自动填充：{auto_description[:60]}"
                f"{'…' if len(auto_description) > 60 else ''}"
            )

        defaults   = {"description": auto_description}
        field_vals = render_field_inputs("upload", defaults=defaults, skip_keys=skip)
        if auto_description:
            field_vals["description"] = auto_description

        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("✅ 完成并归档", use_container_width=True, type="primary"):
                missing = validate_session(field_vals)
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
                missing = validate_session(field_vals)
                if missing:
                    st.warning(f"已暂存，待补充：{', '.join(missing)}")
                else:
                    st.success("已暂存！")
                st.rerun()
