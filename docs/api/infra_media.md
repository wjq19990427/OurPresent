### `backend/infrastructure/media/thumbnails.py` — 媒体工具

负责视频缩略图和图片字节转换。可选依赖 `cv2` / `PIL`，缺失时自动降级。

```python
def video_thumbnail(path)
```

- 提取视频第一帧并叠加 `▶ [视频]` 标签
- 成功时返回 `(PIL Image, "")`
- 失败时返回 `(None, 错误说明)`
- 若未安装 `cv2` / `PIL`，返回 `(None, "⚠ 预览不可用（缺少 cv2/PIL）")`

```python
def pil_to_png_bytes(img) -> bytes
```

- 将 PIL Image 转为 PNG bytes
- 供 `st.image()` 直接展示