### `backend/application/sessions/validation.py` — Session 数据校验

该模块提供 Session 数据完整性和文字型记录判断逻辑，由 session 用例层和前端组件共同使用。

```python
def is_text_session(session: SessionRecord) -> bool
```

- 判断是否为纯文字记录
- 判定条件：
  - `source_type == "text"`；或
  - `files` 中所有文件扩展名都属于 `TEXT_EXTS`
- 返回 `True` 时，`description` 字段在 UI 中可由内容自动填充

```python
def validate_session(session: SessionRecord) -> list[str]
```

- 检查 session 是否缺失必填字段
- 返回值为“未填写字段的中文 label 列表”
- 空列表表示信息完整
- 对纯文字记录会自动跳过 `description`

示例：

```python
validate_session(session_record)
# -> ["创建时间"]
```

---

### `backend/application/sessions/files.py` — Session 附件文件操作

负责 session 附件的命名、写入和删除。

```python
def _safe_filename(name: str) -> str
```

- 内部辅助函数
- 过滤 Windows 非法路径字符：`\ / : * ? " < > |`
- 返回替换后的安全文件名

```python
def write_session_files(
    session_id: str,
    file_data_list: list[tuple[bytes, str]],
    target_dir: Path,
) -> list[dict]
```

- 将一组文件写入目标目录
- 文件命名格式：`{session_id}_{index}_{safe_name}`
- 返回 file 记录列表，例如：

```python
[
    {
        "filename": "20260506_000_photo.jpg",
        "original_name": "photo.jpg",
        "path": "/abs/path/to/file",
    }
]
```

```python
def delete_session_files(session: SessionRecord) -> None
```

- 删除某条 session 关联的所有物理文件
- 同时删除对应 `Final/{session_id}.md`

---

### `backend/application/sessions/markdown.py` — 归档 Markdown 生成

```python
def write_session_markdown(session: SessionRecord) -> None
```

- 根据 session 内容生成归档 Markdown
- 输出文件路径：`Assets/Final/{session_id}.md`
- 内容包括：
  - 上传时间 / 归档时间
  - 字段内容
  - 评论区
  - 编辑历史

---

### `backend/application/sessions/creation.py` — Session 创建流程

```python
def _build_session_base(user_id: str, couple_id: Optional[str]) -> SessionRecord
```

- 内部工厂函数
- 生成一条 session 的默认骨架
- 默认状态包括：
  - `status="pending"`
  - `visibility="private"`
  - 空的 `files`、`comments`、`edit_history`

```python
def save_session_pending(
    user_id: str,
    couple_id: Optional[str],
    file_data_list: list[tuple[bytes, str]],
    source_type: str,
    field_values: dict,
) -> None
```

- 创建 `status="pending"` 的 session
- 文件写入 `Assets/Pending/`
- 将 `field_values` 中合法字段写入 `SessionRecord`
- 根据 `validate_session()` 计算 `is_complete`

```python
def save_session_final(
    user_id: str,
    couple_id: Optional[str],
    file_data_list: list[tuple[bytes, str]],
    source_type: str,
    field_values: dict,
) -> None
```

- 直接创建 `status="final"` 的 session
- 文件写入 `Assets/Final/`
- 写入 `archive_time`
- 立即生成对应 `.md` 归档文件

---

### `backend/application/sessions/editing.py` — Session 编辑与归档

```python
def move_to_final(session_id: str) -> None
```

- 将已有 pending session 归档为 final
- 行为包括：
  - 文件从 `Pending/` 移到 `Final/`
  - `status -> "final"`
  - 写入 `archive_time`
  - 重写对应 `.md`

```python
def update_session_fields(session_id: str, new_values: dict) -> None
```

- 更新 session 字段
- 仅处理 `FIELD_SCHEMA` 中定义的合法字段
- 若该 session 已归档：
  - 计算字段 diff
  - 追加到 `edit_history`
  - 重写对应 `.md`
- 对纯文字 session，不追踪 `description` 的编辑历史
- 更新后重新计算 `is_complete`

```python
def append_to_session(session_id: str, field: str, text: str) -> None
```

- 仅允许 `visibility == "pending_unlock"` 的记录
- `field` 仅允许 `FIELD_SCHEMA` 中的文本类字段：`description` / `feeling` / `reason`
- 将 `text` 追加到原字段内容之后，并写入稳定的「追加于 时间」分隔标记
- 不写入 `edit_history`
- 更新后重新计算 `is_complete`
- 若记录已归档，会同步重写对应 `.md`
- 记录不存在、非 `pending_unlock`、字段不可追加或追加内容为空时抛 `ValueError`

---

### `backend/application/sessions/sharing.py` — 共享与可见性控制

```python
def can_view_session(session: SessionRecord, viewer_id: str) -> bool
```

- 可见性规则：
  - 创建者始终可见
  - 若查看者不存在，返回 `False`
  - 若查看者和记录不属于同一 `couple_id`，返回 `False`
  - 其余情况下，仅 `visibility == "shared"` 时返回 `True`

```python
def request_unlock(session_id: str, unlock_at: str) -> None
```

- `unlock_at` 必填，格式与 `now_str()` 一致：`%Y-%m-%d %H:%M:%S`
- 若记录当前为 `private`：
  - 写入 `unlock_requested_at = now`
  - 当 `unlock_at <= now` 时直接进入 `shared`，并写入 `shared_at = now`、`unlock_at = now`
  - 当 `unlock_at > now` 时进入 `pending_unlock`

```python
def unlock_now(session_id: str) -> None
```

- 仅允许 `visibility == "pending_unlock"` 的记录
- 行为：
  - `visibility -> "shared"`
  - 写入 `shared_at = now`
  - 写入 `unlock_at = now`，保证实际共享时间与开放时间一致
- 保留原有 `unlock_requested_at`
- 记录不存在或非 `pending_unlock` 时抛 `ValueError`

```python
def reschedule_unlock(session_id: str, new_unlock_at: str) -> None
```

- 仅允许 `visibility == "pending_unlock"` 的记录
- `new_unlock_at` 格式与 `now_str()` 一致：`%Y-%m-%d %H:%M:%S`
- 当 `new_unlock_at > now`：
  - 仅更新 `unlock_at = new_unlock_at`
  - `visibility` 保持 `pending_unlock`
  - `unlock_requested_at` 保持不变
- 当 `new_unlock_at <= now`：等同 `unlock_now()`，立即进入 `shared`
- 记录不存在、非 `pending_unlock` 或时间格式无效时抛 `ValueError`

```python
def revoke_unlock(session_id: str) -> None
```

- 将记录从 `pending_unlock` 撤回为 `private`
- 清空 `unlock_requested_at` 和 `unlock_at`

---

### `backend/application/sessions/comments.py` — 评论 CRUD

```python
def add_comment(session_id: str, author_id: str, text: str) -> None
```

- 向 session 评论区追加一条评论
- 评论字段包括：
  - `id`
  - `author`
  - `text`
  - `created_at`
- 若是 final session，会同步重写 `.md`

```python
def delete_comment(session_id: str, comment_id: str) -> None
```

- 删除指定评论
- 若是 final session，会同步重写 `.md`

---

### `backend/application/sessions/export.py` — 导出

```python
def collect_export_files(user_id: str) -> list[Path]
```

- 返回该用户可导出的文件路径列表
- 仅导出 `session.user_id == user_id` 的文件
- 不包含对方数据

---

### `backend/application/sessions/destruction.py` — 销毁

```python
def destroy_couple_data(couple_id: str) -> None
```

- 不可逆销毁操作
- 删除指定情侣关系下的：
  - 所有 sessions
  - 所有磁盘文件
  - 所有归档 `.md`
- 同时：
  - `couple_status -> "dissolved"`
  - 双方 `user.couple_id -> None`
