# API 约定与模块公开接口

## 模块详解

### `backend/config/settings.py` — 全局配置

所有后端模块从这里导入路径常量和字段定义，避免重复定义。

#### 路径常量

```python
BASE_DIR    = Path(... )          # 项目根目录
DATA_DIR    = BASE_DIR / "data"
DB_PATH     = DATA_DIR / "database.db"
LEGACY_DB_PATH = DATA_DIR / "db.json"
ASSETS_DIR  = BASE_DIR / "Assets"
PENDING_DIR = ASSETS_DIR / "Pending"
FINAL_DIR   = ASSETS_DIR / "Final"
```

#### 其他常量

```python
TEXT_EXTS          = {".txt", ".md"}
TOKEN_EXPIRE_HOURS = 24
```

#### `FIELD_SCHEMA`

驱动 UI 渲染、字段校验和 Markdown 归档生成的核心配置。新增元数据字段时，优先在这里追加。

```python
FIELD_SCHEMA: list[dict] = [
    {
        "key": str,
        "label": str,
        "required": bool,
        "type": str,
        "placeholder": str,
        "help": str,
    },
    ...
]
```

`type` 当前可选值：

| type | 渲染控件 | 存储格式 |
|------|----------|----------|
| `"textarea"` | 多行文本框 | `str` |
| `"text"` | 单行文本框 | `str` |
| `"date_or_text"` | 日期选择 + 自由输入 | `str` |

当前默认字段：

| key | label | required | type |
|-----|-------|----------|------|
| `content_time` | 创建时间 | ✅ | `date_or_text` |
| `description` | 描述 | ✅（文件型） | `textarea` |
| `feeling` | 感受 | ✅ | `textarea` |
| `reason` | 记录原因 | ❌ | `textarea` |

---

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
```

- 表示一个注册用户
- `couple_id is None` 表示尚未绑定
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
```

- 表示一条情侣关系或绑定请求
- `user_a` 是发起绑定请求的一方
- `couple_status` 当前可能为：
  - `pending_bind`
  - `active`
  - `frozen`
  - `dissolved`

#### `backend/domain/models/session.py`

```python
class SessionRecord:
    session_id: str
    user_id: str
    couple_id: str | None
    status: str
    visibility: str
    unlock_requested_at: str | None
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

- 表示一条记录（灵感墙或归档区）
- `status`：`pending` 或 `final`
- `visibility`：`private` / `pending_unlock` / `shared`
- `files`、`comments`、`edit_history` 仍保持字典列表，便于兼容现有 UI

#### `backend/domain/models/auth_token.py`

```python
class AuthToken:
    token: str
    user_id: str
    expires_at: str
```

- 表示一个持久化登录 token
- `expires_at` 为字符串时间戳，格式 `%Y-%m-%d %H:%M:%S`

---

### `backend/infrastructure/database/db.py` — 底层 SQLite 读写

负责最底层的 SQLite 文件访问、旧 JSON 自动迁移、目录初始化和通用时间工具。

```python
EMPTY_DB: dict = {"users": [], "couples": [], "sessions": [], "auth_tokens": []}
```

- 空数据库结构常量
- 用于空库、旧格式兼容或迁移失败时的默认返回值

```python
def now_str() -> str
```

- 返回当前时间字符串
- 格式：`%Y-%m-%d %H:%M:%S`

```python
def parse_dt(value: str) -> datetime | None
```

- 解析上述时间格式
- 空字符串或格式错误时返回 `None`

```python
def load_db() -> dict
```

- 读取 `data/database.db`
- 返回顶层包含 `users`、`couples`、`sessions`、`auth_tokens` 的字典
- 若 SQLite 文件不存在，会自动初始化 schema
- 若发现旧版 `data/db.json`，会在空库时自动迁移
- 若读到旧版“纯 sessions 数组”结构，自动兼容为新顶层对象后迁入 SQLite
- 若旧 JSON 损坏或读文件失败，回退为空结构

```python
def save_db(data: dict) -> None
```

- 全量覆盖写回 `data/database.db`
- 当前 alpha 仍保留整库字典式 `load_db()/save_db()` 编程模型，但底层介质已切换为 SQLite

```python
def ensure_dirs() -> None
```

- 确保以下目录存在：
  - `data/`
  - `Assets/Pending/`
  - `Assets/Final/`

---

### `backend/infrastructure/database/users_repo.py` — 用户仓储

负责 `User` 的创建、查询、更新和密码校验。

```python
def _hash_password_with_salt(password: str, salt: str) -> str
```

- 内部密码哈希函数
- 使用 `sha256(salt + password)`

```python
def _hash_password(password: str) -> str
```

- 使用项目当前默认盐值 `ourpresent_salt_v1`
- 当前仅适合本地 demo，生产环境应替换为 `bcrypt` 或 `argon2`

```python
def create_user(username: str, password: str) -> User
```

- 创建新用户并写入 DB
- 自动生成 `user_id = "usr_" + 8位 UUID hex`
- 返回 `User` 对象
- 不负责用户名重复校验，该职责由 `application.auth.register()` 承担

```python
def get_user_by_username(username: str) -> User | None
```

- 按用户名查找用户
- 找到时返回 `User`
- 未找到返回 `None`

```python
def get_user_by_id(user_id: str) -> User | None
```

- 按 `user_id` 查找用户
- 找到时返回 `User`

```python
def verify_password(user: User, password: str) -> bool
```

- 校验输入密码是否匹配
- 同时兼容当前盐值 `ourpresent_salt_v1` 和旧盐值 `projects_salt_v1`

```python
def update_user(user_id: str, fields: dict) -> User | None
```

- 按 `user_id` 局部更新用户记录
- 更新成功返回新的 `User`
- 未找到时返回 `None`

---

### `backend/infrastructure/database/couples_repo.py` — 情侣关系仓储

负责 `Couple` 的创建、查询和状态更新。

```python
def create_couple_request(from_user_id: str, to_user_id: str) -> Couple
```

- 创建一条 `pending_bind` 状态的绑定请求
- `user_a` 记录发起方，`user_b` 记录接收方
- 返回新建的 `Couple`

```python
def get_couple_by_id(couple_id: str) -> Couple | None
```

- 按 `couple_id` 查询情侣关系记录

```python
def get_couple_for_user(user_id: str) -> Couple | None
```

- 返回该用户当前有效的情侣关系
- 仅返回状态为 `pending_bind` / `active` / `frozen` 的记录
- 不返回 `dissolved`

```python
def get_pending_requests_for_user(user_id: str) -> list[Couple]
```

- 返回“发给该用户”的待确认绑定请求列表
- 条件：
  - `couple_status == "pending_bind"`
  - `user_b == user_id`

```python
def accept_couple_request(couple_id: str) -> Couple | None
```

- 接受绑定请求
- 将 `couple_status` 改为 `active`
- 同步将双方 `User.couple_id` 更新为当前 `couple_id`
- 返回更新后的 `Couple`

```python
def reject_couple_request(couple_id: str) -> None
```

- 拒绝绑定请求
- 直接从 DB 中删除对应 `Couple` 记录

```python
def update_couple(couple_id: str, fields: dict) -> Couple | None
```

- 按 `couple_id` 局部更新情侣关系记录
- 找到时保存并返回更新后的 `Couple`
- 未找到返回 `None`

---

### `backend/infrastructure/database/tokens_repo.py` — 登录 Token 仓储

负责持久化登录 token 的创建、查询和撤销。

```python
def create_auth_token(user_id: str) -> AuthToken
```

- 创建 UUID token
- 计算 `expires_at = now + TOKEN_EXPIRE_HOURS`
- 写入 `auth_tokens`
- 返回 `AuthToken` 对象

```python
def get_valid_auth_token(token: str) -> AuthToken | None
```

- 校验 token 是否存在且未过期
- 有效时返回 `AuthToken`
- 无效、空字符串或过期时返回 `None`

```python
def revoke_auth_token(token: str) -> None
```

- 使 token 立即失效
- 退出登录时调用

---

### `backend/infrastructure/database/sessions_repo.py` — Session 仓储

负责 `SessionRecord` 的最小持久化操作。

```python
def add_session(session: SessionRecord) -> None
```

- 将新的 session 追加到 DB
- 不做去重，默认调用方保证 `session_id` 唯一

```python
def list_sessions() -> list[SessionRecord]
```

- 返回当前 DB 中的全部 sessions
- 每项都转换为 `SessionRecord`

```python
def get_session_by_id(session_id: str) -> SessionRecord | None
```

- 按 `session_id` 查找单条 session

```python
def replace_session(session: SessionRecord) -> None
```

- 按 `session_id` 替换现有 session
- 若没找到，不会新增

```python
def list_sessions_for_user(user_id: str) -> list[SessionRecord]
```

- 返回某个用户创建的全部 session
- 当前实现基于 `list_sessions()` 过滤

---

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

---

### `backend/infrastructure/ai/agent_skills.py` — AI 集成边界

第二阶段 AI 接口预留，当前仍是占位实现。

```python
def get_shared_sessions_for_rag(couple_id: str) -> list[dict]
```

- 返回指定情侣关系下所有 `visibility == "shared"` 的 sessions
- 供未来 RAG / 向量索引使用
- 强约束：私密记录不能进入向量库

```python
def get_report_history(couple_id: str) -> list[dict]
```

- 预留给未来“情感周报”或“关系报告”功能
- 当前直接抛 `NotImplementedError`

---

### `backend/application/sessions/validation.py` — Session 数据校验

该模块提供 Session 数据完整性和文字型记录判断逻辑，由 session 用例层和前端组件共同使用。

```python
def is_text_session(session: dict) -> bool
```

- 判断是否为纯文字记录
- 判定条件：
  - `source_type == "text"`；或
  - `files` 中所有文件扩展名都属于 `TEXT_EXTS`
- 返回 `True` 时，`description` 字段在 UI 中可由内容自动填充

```python
def validate_session(session: dict) -> list[str]
```

- 检查 session 是否缺失必填字段
- 返回值为“未填写字段的中文 label 列表”
- 空列表表示信息完整
- 对纯文字记录会自动跳过 `description`

示例：

```python
validate_session({"content_time": "", "description": "内容", "feeling": "快乐"})
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
def delete_session_files(session: dict) -> None
```

- 删除某条 session 关联的所有物理文件
- 同时删除对应 `Final/{session_id}.md`

---

### `backend/application/sessions/markdown.py` — 归档 Markdown 生成

```python
def write_session_markdown(session: dict) -> None
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

---

### `backend/application/sessions/sharing.py` — 共享与可见性控制

```python
def can_view_session(session: dict, viewer_id: str) -> bool
```

- 可见性规则：
  - 创建者始终可见
  - 若查看者不存在，返回 `False`
  - 若查看者和记录不属于同一 `couple_id`，返回 `False`
  - 其余情况下，仅 `visibility == "shared"` 时返回 `True`

```python
def request_unlock(session_id: str) -> None
```

- 将记录从 `private` 改为 `pending_unlock`
- 写入 `unlock_requested_at`

```python
def revoke_unlock(session_id: str) -> None
```

- 将记录从 `pending_unlock` 撤回为 `private`
- 清空 `unlock_requested_at`

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

---

### `backend/application/auth/errors.py` — 认证异常

```python
class AuthError(Exception)
```

- 注册 / 登录失败时抛出

---

### `backend/application/auth/commands.py` — 注册与登录

```python
def register(username: str, password: str) -> User
```

- 校验用户名和密码合法性：
  - 用户名长度 2-20
  - 密码至少 6 位
  - 用户名不能重复
- 校验通过后调用 `users_repo.create_user()`
- 返回 `User`

```python
def login(username: str, password: str) -> User
```

- 按用户名查询用户
- 校验密码
- 成功返回 `User`
- 失败抛 `AuthError`

---

### `backend/application/auth/tokens.py` — 登录 token 用例

```python
def create_auth_token(user_id: str) -> str
```

- 创建登录 token
- 内部调用 `tokens_repo.create_auth_token()`
- 对外只返回 token 字符串

```python
def validate_auth_token(token: str) -> User | None
```

- 先校验 token 是否存在且未过期
- 有效时再根据 `user_id` 取回 `User`
- 无效时返回 `None`

```python
def revoke_auth_token(token: str) -> None
```

- 撤销登录 token
- 退出登录时调用

---

### `backend/application/couples/errors.py` — 情侣关系异常

```python
class CoupleError(Exception)
```

- 绑定 / 解绑 / 冻结相关业务失败时抛出

---

### `backend/application/couples/policies.py` — 关系规则判断

```python
def ensure_can_send_bind_request(from_user_id: str, to_user_id: str) -> None
```

- 业务校验：
  - 不能给自己发绑定请求
  - 目标用户必须存在
  - 双方都不能已有 `active` / `frozen` / `pending_bind` 关系
- 校验失败时抛 `CoupleError`

```python
def ensure_can_start_uncouple(user_id: str) -> None
```

- 发起冻结式解绑前的校验
- 要求当前存在绑定关系
- 若已处于冻结期则抛 `CoupleError`

```python
def ensure_can_confirm_uncouple(user_id: str) -> None
```

- 发起“双方同意立即销毁”前的校验
- 要求当前存在绑定关系

---

### `backend/application/couples/binding.py` — 绑定流程

```python
def send_bind_request(from_user_id: str, to_user_id: str) -> Couple
```

- 先执行 `ensure_can_send_bind_request()`
- 校验通过后调用 `couples_repo.create_couple_request()`
- 返回新建的 `Couple`

```python
def accept_bind(couple_id: str) -> None
```

- 接受绑定请求
- 调用 `accept_couple_request()`

```python
def reject_bind(couple_id: str) -> None
```

- 拒绝绑定请求
- 调用 `reject_couple_request()`

---

### `backend/application/couples/uncoupling.py` — 解绑与冻结期

```python
def start_uncouple(user_id: str) -> None
```

- 单方发起分手
- 要求当前必须处于 `active` 关系中
- 通过后将 couple 更新为：
  - `couple_status = "frozen"`
  - 记录 `uncouple_initiated_by`
  - 记录 `uncouple_initiated_at`
  - 设置 `freeze_ends_at = now + 90 天`

```python
def confirm_uncouple(user_id: str) -> None
```

- 双方同意立即解绑
- 要求当前必须存在绑定关系
- 通过后将 `both_agreed_uncouple = True`
- 随后立即调用 `destroy_couple_data()`

```python
def is_frozen(user_id: str) -> bool
```

- 判断当前用户所在关系是否处于冻结期
- UI 层用它决定是否只读

---

### `backend/application/maintenance/ticking.py` — 生命周期推进

负责自动状态推进，不直接处理 UI。

```python
def tick(db: dict) -> bool
```

- 在已加载的 `db` 对象上原地推进状态
- 若有变化返回 `True`
- 处理三类事情：
  1. `pending_unlock` 满 90 天后推进为 `shared`
  2. `frozen` 到期后自动调用 `destroy_couple_data()`
  3. 清理过期 `auth_tokens`

```python
def load_db_with_tick() -> dict
```

- 加载 DB
- 调用 `tick()`
- 若有变化则保存并重新加载一次
- UI 层应优先调用这个函数，而不是直接调用 `load_db()`

---

### `frontend/streamlit_app/components.py` — Streamlit UI 组件

所有函数都依赖已登录的 `st.session_state["user"]`。

#### 会话状态工具

```python
def _current_user() -> Optional[User]
```

- 返回 `st.session_state["user"]`

```python
def _uid() -> str
```

- 返回当前用户 `user_id`

```python
def _is_frozen() -> bool
```

- 返回当前用户是否处于冻结期

```python
def _couple() -> Optional[Couple]
```

- 返回当前用户对应的情侣关系对象

```python
def _partner_id() -> Optional[str]
```

- 在 `active` 关系下返回伴侣 `user_id`
- 未绑定或非激活状态返回 `None`

#### 显示辅助

```python
def _session_thumb(session: dict)
```

- 返回 `(缩略图, 文本标签)`
- 行为：
  - 图片：返回 PIL Image
  - 视频：调用 `video_thumbnail()`
  - 文本：返回文本预览
  - 无文件：回退到 `description` 预览

```python
def _days_until_unlock(session: dict) -> int
```

- 基于 `upload_time` 计算距离满 90 天还剩几天

```python
def _visibility_badge(session: dict) -> str
```

- 返回可见性标签：
  - `🔒 私密`
  - `⏳ 待解锁（还需 N 天）`
  - `✅ 已共享`

```python
def _looks_like_date(value: str) -> bool
```

- 判断字符串是否符合 `YYYY-MM-DD` 格式

#### 表单渲染

```python
def render_field_inputs(
    prefix: str,
    defaults: Optional[dict] = None,
    skip_keys: Optional[set] = None,
) -> dict
```

- 遍历 `FIELD_SCHEMA` 生成输入控件
- 通常在 `st.form()` 中调用
- 返回值是字段值字典

参数说明：

| 参数 | 说明 |
|------|------|
| `prefix` | widget key 前缀，需保证同页唯一 |
| `defaults` | 默认值，常用于编辑态回填 |
| `skip_keys` | 跳过渲染的字段集合 |

#### 评论区

```python
def render_comments(session: dict) -> None
```

- 渲染评论列表
- 提供删除按钮和新增评论输入区
- 发送评论时调用 `add_comment()`

#### Session 卡片

```python
def render_card(col, session: dict, state_key: str) -> None
```

- 在指定列容器中渲染 session 卡片
- 展示缩略图、文件数、评论数、隐私状态、完整度
- 点击按钮后把 `session_id` 写入 `st.session_state[state_key]`

#### Session 详情区

```python
def render_detail(session: dict, mode: str, read_only: bool = False) -> None
```

- 渲染详情、预览、编辑历史、编辑表单和评论区

参数说明：

| 参数 | 说明 |
|------|------|
| `mode` | `"pending"` 或 `"final"` |
| `read_only` | 冻结期或查看对方共享记录时为 `True` |

行为说明：

- `read_only=False` 时可编辑字段
- `mode="pending"` 时支持“完成并归档”
- 自己的记录可申请共享或撤回共享
- 纯文字记录的 `description` 不可手动修改

---

### `frontend/streamlit_app/pages/` — 页面模块

每个页面函数负责组织 UI 交互，不承载核心业务规则。

```python
def render_upload_tab() -> None
```

- Tab 1「🗂️ 记录舱」
- 支持上传文件或粘贴文字
- 可选择“完成并归档”或“暂存到待处理”
- 调用：
  - `save_session_final()`
  - `save_session_pending()`

```python
def render_pending_tab(db: dict) -> None
```

- Tab 2「🖼️ 灵感墙」
- 展示当前用户所有 `status == "pending"` 的记录
- 点击卡片后调用 `render_detail(..., mode="pending")`

```python
def render_archived_tab(db: dict) -> None
```

- Tab 3「📚 已归档」
- 展示当前用户所有 `status == "final"` 的记录
- 点击卡片后调用 `render_detail(..., mode="final")`

```python
def render_shared_tab(db: dict) -> None
```

- Tab 4「💌 情侣空间」
- 仅展示伴侣共享给自己的 `visibility == "shared"` 记录
- 使用 `can_view_session()` 做二次权限校验
- 全部只读查看

```python
def render_account_tab(db: dict) -> None
```

- Tab 5「⚙️ 账户」
- 包含：
  - 当前账户信息
  - 收到的绑定请求
  - 情侣关系面板
  - 分手协议入口
  - 冻结期导出入口

情侣状态对应 UI：

| `couple_status` | 展示内容 |
|-----------------|----------|
| 无关系 | 输入伴侣 ID 并发送绑定请求 |
| `pending_bind` | 发送方显示等待提示，接收方显示接受/拒绝引导 |
| `active` | 展示已绑定信息和解绑入口 |
| `frozen` | 展示冻结提示和导出入口 |

---

### `main.py` — 应用入口

```python
def _init_state() -> None
```

- 初始化 `st.session_state` 默认键：
  - `user`
  - `upload_key`
  - `pending_selected`
  - `archived_selected`
  - `shared_selected`
  - `auth_tab`
- 若 URL 中存在 `token`，尝试自动恢复登录

```python
def render_auth_page() -> None
```

- 渲染登录 / 注册页
- 登录成功后：
  - 调用 `create_auth_token()`
  - 将 token 写入 `st.query_params`
  - 保存当前 `User` 到 `session_state`

```python
def main() -> None
```

- 应用主入口
- 调用顺序大致为：
  1. `ensure_dirs()`
  2. `_init_state()`
  3. 未登录则显示 `render_auth_page()`
  4. 已登录则调用 `load_db_with_tick()`
  5. 渲染五个主 Tab

当前 `st.session_state` 关键键：

| 键名 | 类型 | 说明 |
|------|------|------|
| `user` | `User | None` | 当前登录用户 |
| `upload_key` | `int` | 上传控件重置计数器 |
| `pending_selected` | `str | None` | 灵感墙当前选中的 `session_id` |
| `archived_selected` | `str | None` | 已归档当前选中的 `session_id` |
| `shared_selected` | `str | None` | 情侣空间当前选中的 `session_id` |
| `auth_tab` | `str` | 登录页内部标签状态 |

---

## 当前层次约束

```text
frontend/streamlit_app
  -> backend/application
  -> backend/config
  -> backend/infrastructure（查询型依赖）

backend/application
  -> backend/infrastructure
  -> backend/domain
  -> backend/config

backend/infrastructure
  -> backend/domain
  -> backend/config
```

## 后续建议

- 新增 HTTP API 时，从 `backend/api/` 开始接线，不要把路由逻辑写回 `main.py`
- 新增数据库或对象存储实现时，优先新增 `backend/infrastructure/*` 适配器
- 新增领域对象时，优先放到 `backend/domain/models/`
- 新增业务规则时，优先放到 `backend/application/*`
- 模块接口发生变化时，同步更新本文件，避免文档只剩目录不剩语义
