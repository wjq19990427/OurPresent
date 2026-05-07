"""Render archived sessions to markdown files."""

from __future__ import annotations

from backend.config.settings import FIELD_SCHEMA, FINAL_DIR


def write_session_markdown(session: dict) -> None:
    names = [file_record["original_name"] for file_record in session.get("files", [])]
    title = names[0] if names else session["session_id"]
    count = len(names)
    lines = [
        f"# {title}（共 {count} 个文件）\n",
        f"**上传时间**：{session.get('upload_time', '')}\n",
        f"**归档时间**：{session.get('archive_time', '')}\n",
    ]
    for field in FIELD_SCHEMA:
        value = session.get(field["key"], "")
        if value:
            lines += [f"\n## {field['label']}\n", f"{value}\n"]

    comments = session.get("comments", [])
    if comments:
        lines.append("\n---\n\n## 评论区\n")
        for comment in comments:
            lines += [f"\n**{comment['created_at']}**\n\n{comment['text']}\n"]

    history = session.get("edit_history", [])
    if history:
        lines.append("\n---\n\n## 编辑历史\n")
        for entry in reversed(history):
            lines.append(f"\n### {entry['edited_at']}\n")
            for key, value in entry["changes"].items():
                label = next((field["label"] for field in FIELD_SCHEMA if field["key"] == key), key)
                lines.append(f"- **{label}**：「{value['from']}」→「{value['to']}」\n")

    md_path = FINAL_DIR / f"{session['session_id']}.md"
    md_path.write_text("".join(lines), encoding="utf-8")
