"""Media preview and conversion helpers."""

from __future__ import annotations

import io

try:
    import cv2
    from PIL import Image, ImageDraw

    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False


def video_thumbnail(path):
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
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
