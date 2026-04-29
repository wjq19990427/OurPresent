"""
文件写入、视频缩略图提取、PIL 工具函数。
不依赖任何内部模块，可独立导入。
"""

from __future__ import annotations

import io
from pathlib import Path

try:
    import cv2
    from PIL import Image, ImageDraw
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False


def _safe_filename(name: str) -> str:
    """过滤 Windows 非法路径字符。"""
    illegal = r'\/:*?"<>|'
    for ch in illegal:
        name = name.replace(ch, "_")
    return name


def write_files(
    session_id: str,
    file_data_list: list[tuple[bytes, str]],
    target_dir: Path,
) -> list[dict]:
    """将文件列表写入 target_dir，返回 file 记录列表。"""
    result = []
    for i, (data, original_name) in enumerate(file_data_list):
        safe_name = _safe_filename(original_name)
        stored    = f"{session_id}_{i:03d}_{safe_name}"
        dest      = target_dir / stored
        dest.write_bytes(data)
        result.append({
            "filename":      stored,
            "original_name": original_name,
            "path":          str(dest),
        })
    return result


def video_thumbnail(path: Path):
    """提取视频第一帧，叠加「▶ [视频]」标签，返回 (PIL Image | None, label)。"""
    if not _CV2_AVAILABLE:
        return None, "⚠ 预览不可用（缺少 cv2/PIL）"
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


def pil_to_png_bytes(img) -> bytes:
    """PIL Image → PNG bytes，供 st.image() 使用。"""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
