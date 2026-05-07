"""Session attachment file operations."""

from __future__ import annotations

from pathlib import Path

from backend.config.settings import FINAL_DIR


def _safe_filename(name: str) -> str:
    illegal = r'\/:*?"<>|'
    for char in illegal:
        name = name.replace(char, "_")
    return name


def write_session_files(
    session_id: str,
    file_data_list: list[tuple[bytes, str]],
    target_dir: Path,
) -> list[dict]:
    result = []
    for index, (data, original_name) in enumerate(file_data_list):
        safe_name = _safe_filename(original_name)
        stored = f"{session_id}_{index:03d}_{safe_name}"
        dest = target_dir / stored
        dest.write_bytes(data)
        result.append(
            {
                "filename": stored,
                "original_name": original_name,
                "path": str(dest),
            }
        )
    return result


def delete_session_files(session: dict) -> None:
    for file_record in session.get("files", []):
        path = Path(file_record.get("path", ""))
        if path.exists():
            path.unlink(missing_ok=True)
    md_path = FINAL_DIR / f"{session['session_id']}.md"
    md_path.unlink(missing_ok=True)
