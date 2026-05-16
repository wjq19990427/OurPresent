### `backend/domain/models/*.py` — 领域模型

当前领域模型统一使用 `@dataclass(slots=True)`，并提供 `from_dict()` / `to_dict()`，用于在 SQLite 记录导出字典和业务对象之间转换。

#### `backend/domain/models/user.py`

```python
class User:
    user_id: str
    username: str
    password_hash: str
    couple_id: str | None
    joined_at: str
    weekly_report_enabled: bool
```

- 表示一个注册用户
- `couple_id is None` 表示尚未绑定
- `weekly_report_enabled` 表示当前用户是否开启情感周报服务，旧数据默认 `False`
- `from_dict()` 从持久化字典记录恢复对象
- `to_dict()` 将对象转回可写入 DB 的字典

#### `backend/domain/models/couple.py`

```python
class Couple:
    couple_id: str
    user_a: str
    user_b: str
    created_at: str
    couple_status: str
    uncouple_initiated_by: str | None
    uncouple_initiated_at: str | None
    both_agreed_uncouple: bool
    freeze_ends_at: str | None
    cancel_uncouple_requested_by: str | None
    cancel_uncouple_requested_at: str | None
    destroy_uncouple_requested_by: str | None
    destroy_uncouple_requested_at: str | None
    weekly_report_interval_days: int
```

- 表示一条情侣关系或绑定请求
- `user_a` 是发起绑定请求的一方
- `couple_status` 当前可能为：
  - `pending_bind`
  - `active`
  - `frozen`
  - `dissolved`
- `cancel_uncouple_requested_by` / `cancel_uncouple_requested_at` 表示冻结期内“撤回冻结”请求的发起者与发起时间；为空表示当前没有待回应请求
- `destroy_uncouple_requested_by` / `destroy_uncouple_requested_at` 表示冻结期内“现在分手”申请的发起者与发起时间；为空表示当前没有待回应申请
- `weekly_report_interval_days` 是双方共享的情感周报间隔天数，默认 `7`

#### `backend/domain/models/report.py`

```python
class Report:
    report_id: str
    couple_id: str
    window_start: str
    window_end: str
    generated_at: str
    model_version: str
    footprint: dict
    weather: dict
    resonance: list[dict]
    suspense: list[dict]
    status: str
    source_session_ids: list[str]
```

- 表示一份情感周报
- `report_id` 命名规则为 `rpt_YYYYMMDD_<couple_id>`
- `window_start` / `window_end` / `generated_at` 使用 `%Y-%m-%d %H:%M:%S` 字符串格式
- `model_version` 由后续生成用例填入；未接入模型前允许为空串
- `footprint` / `weather` / `resonance` / `suspense` 承载周报四个模块的结构化 JSON
- `status` 当前约定为 `ready` / `failed` / `sparse`
- `source_session_ids` 记录生成报告使用的 session id 列表，供审计使用
- `from_dict()` / `to_dict()` 仅在持久化边界使用

#### `backend/domain/models/session.py`

```python
class SessionRecord:
    session_id: str
    user_id: str
    couple_id: str | None
    status: str
    visibility: str
    unlock_requested_at: str | None
    unlock_at: str | None
    shared_at: str | None
    upload_time: str
    archive_time: str
    is_complete: bool
    edit_history: list[dict]
    files: list[dict]
    source_type: str
    content_time: str
    description: str
    feeling: str
    reason: str
    comments: list[dict]
```

- 表示一条记录（草稿或归档）
- `status`：`pending` 或 `final`
- `visibility`：`private` / `pending_unlock` / `shared`
- `upload_time`：记录创建/上传时间，不参与共享解锁计算
- `unlock_requested_at`：用户发起共享申请的时间
- `unlock_at`：用户指定的对伴侣开放时间；为空表示未设置共享开放时间
- `shared_at`：记录实际进入 `shared` 的时间
- `visibility == "pending_unlock"` 时，用户可追加文本内容、修改 `unlock_at`、立即解锁或撤回申请
- 立即解锁或把 `unlock_at` 改到过去时，`shared_at` 与 `unlock_at` 会同步写为同一个当前时间
- `files`、`comments`、`edit_history` 仍保持字典列表，便于兼容现有 UI
- `from_dict()` / `to_dict()` 仅由 `sessions_repo` 在持久化边界使用，application 与 frontend 层以 `SessionRecord` 传递

#### `backend/domain/models/auth_token.py`

```python
class AuthToken:
    token: str
    user_id: str
    expires_at: str
```

- 表示一个持久化登录 token
- `expires_at` 为字符串时间戳，格式 `%Y-%m-%d %H:%M:%S`
