# API 约定与模块公开接口

## 模块详解

### core/config.py — 全局配置

所有模块从这里导入路径常量和字段定义，**不在其他地方重复定义**。

#### 路径常量

```python
BASE_DIR    = Path(__file__).parent.parent   # 项目根目录
DATA_DIR    = BASE_DIR / "data"
DB_PATH     = DATA_DIR / "db.json"
ASSETS_DIR  = BASE_DIR / "Assets"
PENDING_DIR = ASSETS_DIR / "Pending"
FINAL_DIR   = ASSETS_DIR / "Final"
```

#### 其他常量

```python
TEXT_EXTS          = {".txt", ".md"}   # 纯文字扩展名集合
TOKEN_EXPIRE_HOURS = 24                # 登录 Token 有效期（小时）
```

#### FIELD_SCHEMA

驱动 UI 渲染、字段校验和 Markdown 生成的核心配置。**新增元数据字段只需在此处追加，无需修改其他代码**。

```python
FIELD_SCHEMA: list[dict] = [
    {
        "key":         str,   # 字段唯一标识，对应 session dict 的键名
        "label":       str,   # 界面显示名称
        "required":    bool,  # True = 必填（纯文字记录的 description 自动豁免）
        "type":        str,   # 控件类型，见下表
        "placeholder": str,   # 输入框占位文字
        "help":        str,   # 字段说明小字
    },
    ...
]
```

**`type` 可选值**

| type | 渲染控件 | 存储格式 |
|------|----------|----------|
| `"textarea"` | 多行文本框 | `str` |
| `"text"` | 单行文本框 | `str` |
| `"date_or_text"` | 日历 + 自由输入双控件 | `str`（ISO 日期或自由文本） |

**当前默认字段**

| key | label | required | type |
|-----|-------|----------|------|
| `content_time` | 创建时间 | ✅ | `date_or_text` |
| `description` | 描述 | ✅（文件型） | `textarea` |
| `feeling` | 感受 | ✅ | `textarea` |
| `reason` | 记录原因 | ❌ | `textarea` |

---

### core/state_machine.py — 状态机

每次页面加载时由 `main.py` 调用，推进两类自动状态转换。

```python
def tick(db: dict) -> bool
```

在已加载的 `db` 对象上**原地**推进以下逻辑，有变化返回 `True`（调用方负责 `save_db`）：

1. **时间锁**：`visibility == "pending_unlock"` 且 `upload_time` 距今 ≥ 90 天 → 推进至 `"shared"`，写入 `shared_at`
2. **冻结期到期**：`couple_status == "frozen"` 且 `freeze_ends_at ≤ now()` → 调用 `session_manager.destroy_couple_data()`
3. **过期 Token 清理**：从 `auth_tokens` 列表中移除 `expires_at ≤ now()` 的条目

```python
def load_db_with_tick() -> dict
```

加载 DB 并推进状态机，**UI 层应始终调用此函数**，不直接调用 `db_manager.load_db()`。

---

### core/agent_skills.py — AI 接口预留

第二阶段 LLM 功能的占位存根，当前均未实现。

```python
def get_shared_sessions_for_rag(couple_id: str) -> list[dict]
```
返回指定情侣关系下所有 `visibility == "shared"` 的 sessions，供 RAG 向量化索引。  
**强约束**：私密记录严禁进入向量库，此函数已在过滤层强制执行。

```python
def get_report_history(couple_id: str) -> list[dict]
```
返回历史周报记录（第二阶段新增 `reports` 表后实现，当前抛 `NotImplementedError`）。

---

### utils/validators.py — 字段校验

无任何内部模块依赖，可独立单元测试。

```python
def _is_text_session(session: dict) -> bool
```
判断是否为纯文字记录：`source_type == "text"` 或全部文件均为 `.txt` / `.md`。  
返回 `True` 时，`description` 字段由内容自动填充，UI 隐藏输入框，编辑历史不追踪该字段变更。

```python
def validate_session(session: dict) -> list[str]
```
检查必填项是否已填写，返回**未填写的必填字段 label 列表**；空列表表示信息完整。纯文字记录中 `description` 自动从必填列表中豁免。

```python
# 示例
validate_session({"content_time": "", "description": "内容", "feeling": "快乐"})
# → ["创建时间"]
```

---

### utils/file_processor.py — 文件工具

无任何内部模块依赖。可选依赖 `cv2` 和 `PIL`，未安装时降级处理。

```python
def write_files(
    session_id: str,
    file_data_list: list[tuple[bytes, str]],
    target_dir: Path,
) -> list[dict]
```
将文件列表写入 `target_dir`，以 `session_id_index_safename` 格式命名，返回 file 记录列表：
```python
[{"filename": "20260430_120000_000_photo.jpg", "original_name": "photo.jpg", "path": "..."}]
```

```python
def video_thumbnail(path: Path) -> tuple[Image | None, str]
```
提取视频第一帧，叠加「▶ [视频]」标签，返回 `(PIL Image, "")` 或 `(None, 错误说明)`。

```python
def pil_to_png_bytes(img: Image) -> bytes
```
将 PIL Image 转换为 PNG bytes，供 `st.image()` 直接使用。

---

### backend/db_manager.py — 数据库层

不依赖 Streamlit，**可直接作为后端 API 的数据访问层复用**。

#### 数据库操作

```python
def load_db() -> dict
```
读取 `data/db.json`，返回含 `users`、`couples`、`sessions`、`auth_tokens` 四个列表的字典。文件不存在或损坏时返回空结构，自动兼容旧版纯数组格式。

```python
def save_db(data: dict) -> None
```
全量写入 `data/db.json`（UTF-8，中文不转义，缩进 2）。

```python
def ensure_dirs() -> None
```
确保 `data/`、`Assets/Pending/`、`Assets/Final/` 目录存在，应用启动时调用一次。

#### 工具函数

```python
def _now_str() -> str             # → "2026-04-30 12:00:00"
def _parse_dt(s: str) -> datetime | None   # 解析上述格式，失败返回 None
```

#### 用户 CRUD

```python
def create_user(username: str, password: str) -> dict
```
创建新用户，返回 user 记录。调用方须确保 `username` 唯一（由 `auth_manager.register` 负责校验）。

```python
def get_user_by_username(username: str) -> dict | None
def get_user_by_id(user_id: str) -> dict | None
def verify_password(user: dict, password: str) -> bool
```

#### 情侣绑定 CRUD

```python
def send_couple_request(from_user_id: str, to_user_id: str) -> dict
```
创建 `couple_status = "pending_bind"` 的 couple 记录，返回该记录。

```python
def get_couple_for_user(user_id: str) -> dict | None
```
返回该用户当前有效的 couple 记录（`pending_bind` / `active` / `frozen`），不返回已解散的关系。

```python
def get_pending_requests_for_user(user_id: str) -> list[dict]
```
返回目标为该用户且状态为 `pending_bind` 的请求列表。

```python
def accept_couple_request(couple_id: str) -> None  # couple_status → "active"，双方 user 更新 couple_id
def reject_couple_request(couple_id: str) -> None  # 从 DB 中删除该 couple 记录
def get_couple_by_id(couple_id: str) -> dict | None
```

#### 登录 Token

```python
def create_auth_token(user_id: str) -> str
```
创建 UUID token，写入 `auth_tokens` 表（含 `expires_at`），返回 token 字符串。

```python
def validate_auth_token(token: str) -> dict | None
```
校验 token 有效性：存在且未过期则返回对应 user 记录，否则返回 `None`。

```python
def revoke_auth_token(token: str) -> None
```
使 token 立即失效（退出登录时调用）。

---

### backend/session_manager.py — Session 管理

包含 Session 的完整生命周期、评论、可见性控制、数据销毁和解绑协议。

#### Session 生命周期

```python
def save_session_pending(
    user_id: str,
    couple_id: str | None,
    file_data_list: list[tuple[bytes, str]],  # [(文件字节, 原始文件名)]
    source_type: str,                          # "file" | "text"
    field_values: dict,
) -> None
```
暂存到 `Assets/Pending/`，创建 `status="pending"` 的 session 记录。

```python
def save_session_final(
    user_id, couple_id, file_data_list, source_type, field_values
) -> None
```
直接归档到 `Assets/Final/`，创建 `status="final"` 的 session 记录，同时生成 `.md` 文件。

```python
def move_to_final(session_id: str) -> None
```
将 Pending session 升级为 Final：移动文件、更新状态、生成 `.md`。

```python
def update_session_fields(session_id: str, new_values: dict) -> None
```
更新字段值。对 `final` 记录计算 diff 并追加 `edit_history`，同时重写 `.md`。

#### 可见性控制（时间锁）

```python
def request_unlock(session_id: str) -> None   # private → pending_unlock
def revoke_unlock(session_id: str) -> None    # pending_unlock → private
```

#### 评论 CRUD

```python
def add_comment(session_id: str, author_id: str, text: str) -> None
def delete_comment(session_id: str, comment_id: str) -> None
```
Final 记录的评论变更会同步重写对应的 `.md` 文件。

#### 数据导出与销毁

```python
def collect_export_files(user_id: str) -> list[Path]
```
返回该用户可导出的文件路径列表（仅 `session.user_id == user_id` 的文件，不含对方数据）。

```python
def destroy_couple_data(couple_id: str) -> None
```
**不可逆操作**：删除该情侣关系下所有 sessions 及磁盘文件，`couple_status` → `"dissolved"`，双方 `couple_id` 置 `null`。

#### 解绑协议

```python
def initiate_uncouple(user_id: str) -> None
```
单方发起分手：`couple_status` → `"frozen"`，记录 `freeze_ends_at`（当前时间 + 90 天）。

```python
def agree_uncouple(user_id: str) -> None
```
对方确认解绑：标记 `both_agreed_uncouple = True`，立即调用 `destroy_couple_data()`。

---

### backend/auth_manager.py — 鉴权层

封装业务校验逻辑，**不直接操作 `st.session_state`**。失败时抛出异常，不返回错误码。

#### 异常类

```python
class AuthError(Exception): ...   # 注册/登录失败
class CoupleError(Exception): ... # 情侣绑定/解绑操作失败
```

#### 注册 / 登录

```python
def register(username: str, password: str) -> dict
```
校验：用户名 2-20 字符、密码 ≥ 6 位、用户名不重复。通过后调用 `db_manager.create_user()`。

```python
def login(username: str, password: str) -> dict
```
校验：用户名存在且密码匹配。返回 user 记录，失败抛 `AuthError`。

#### 情侣绑定

```python
def send_bind_request(from_user_id: str, to_user_id: str) -> dict
```
业务校验：不能向自己发送、目标用户存在、双方均无其他活跃或冻结关系。通过后调用 `db_manager.send_couple_request()`。

```python
def accept_bind(couple_id: str) -> None
def reject_bind(couple_id: str) -> None
```

#### 解绑协议

```python
def start_uncouple(user_id: str) -> None
```
校验：存在绑定关系且不处于冻结期。通过后调用 `session_manager.initiate_uncouple()`。

```python
def confirm_uncouple(user_id: str) -> None
```
校验：存在绑定关系。通过后调用 `session_manager.agree_uncouple()`。

#### 视图权限

```python
def can_view_session(session: dict, viewer_id: str) -> bool
```
创建者始终可见；情侣对方仅在 `visibility == "shared"` 时可见；其他用户不可见。

```python
def is_frozen(user_id: str) -> bool
```
判断当前用户所在的情侣关系是否处于冻结期，供 UI 层决定是否禁用写操作。

---

### frontend/components.py — UI 组件

所有可复用 UI 函数，依赖已登录的 `st.session_state["user"]`。

#### 会话状态工具

```python
def _current_user() -> dict | None   # st.session_state["user"]
def _uid() -> str                     # 当前用户 user_id
def _is_frozen() -> bool              # 当前用户是否处于冻结期
def _couple() -> dict | None          # 当前用户的 couple 记录
def _partner_id() -> str | None       # 伴侣的 user_id（仅 active 状态返回）
```

#### 显示辅助

```python
def _session_thumb(session: dict) -> tuple[Image | None, str]
```
返回 `(缩略图, 标签文字)`：图片返回 PIL Image，视频返回带「▶」标记的帧，文本返回预览文字。

```python
def _visibility_badge(session: dict) -> str
```
返回可见性状态标签：`"🔒 私密"` / `"⏳ 待解锁（还需 N 天）"` / `"✅ 已共享"`。

```python
def _days_until_unlock(session: dict) -> int
```
基于 `upload_time` 计算距满 90 天还剩多少天。

```python
def _pil_to_bytes(img: Image) -> bytes   # PIL Image → PNG bytes
```

#### 字段渲染（form 内）

```python
def render_field_inputs(
    prefix: str,
    defaults: dict | None = None,
    skip_keys: set | None = None,
) -> dict
```
遍历 `FIELD_SCHEMA` 渲染所有字段控件，**必须在 `with st.form():` 块内调用**。

| 参数 | 说明 |
|------|------|
| `prefix` | Widget key 前缀，同页面多处调用时须保证唯一 |
| `defaults` | 字段预填值（编辑场景传入已有 session dict） |
| `skip_keys` | 跳过渲染的字段 key 集合；跳过字段仍以 `defaults` 值返回，不丢失 |

#### 评论区（form 外部）

```python
def render_comments(session: dict) -> None
```
**必须在 `st.form` 外部调用**。渲染评论列表（含评论者用户名）、删除按钮、新评论输入框。

#### Session 卡片

```python
def render_card(col, session: dict, state_key: str) -> None
```
在 `st.columns` 对象中渲染 session 卡片，点击「查看/编辑」将 `session_id` 写入 `st.session_state[state_key]`。

#### Session 详情区

```python
def render_detail(session: dict, mode: str, read_only: bool = False) -> None
```

| `mode` | `read_only` | 说明 |
|--------|-------------|------|
| `"pending"` | `False` | 可编辑，支持暂存和归档 |
| `"final"` | `False` | 可编辑，保存时追加 edit_history |
| `"final"` | `True` | 冻结期只读；或查看对方共享内容 |

自己的记录在详情区显示可见性控制按钮（申请共享 / 撤回申请）。

---

### frontend/pages/ — Tab 页面

每个文件对应一个主 Tab，各自导入所需的 backend 函数和 components。

| 文件 | 函数 | Tab |
|------|------|-----|
| `tab_upload.py` | `render_upload_tab()` | 🗂️ 记录舱 |
| `tab_pending.py` | `render_pending_tab(db)` | 🖼️ 灵感墙 |
| `tab_final.py` | `render_archived_tab(db)` | 📚 已归档 |
| `tab_shared.py` | `render_shared_tab(db)` | 💌 情侣空间 |
| `tab_account.py` | `render_account_tab(db)` | ⚙️ 账户 |

各 Tab 函数接收已加载的 `db` 字典（由 `main.py` 通过 `load_db_with_tick()` 获取后传入），不在内部再次读取数据库，避免重复 I/O。

**Tab 4 — 💌 情侣空间**

仅展示伴侣 `visibility == "shared"` 的记录，调用 `auth_manager.can_view_session()` 进行二次权限校验。全部只读，可发表评论。

**Tab 5 — ⚙️ 账户**

| 区块 | 内容 |
|------|------|
| 我的账户 | 用户名和 ID 展示，退出登录 |
| 收到的绑定请求 | 逐条接受/拒绝 `pending_bind` 请求 |
| 情侣关系面板 | 根据 `couple_status` 展示对应面板 |

| `couple_status` | 展示内容 |
|-----------------|----------|
| 无关系 | 输入伴侣 ID 发送绑定请求 |
| `pending_bind` | 发送方：等待确认提示；接收方：跳转引导 |
| `active` | 已绑定信息 + 解绑协议入口 |
| `frozen` | 冻结期倒计时 + 数据导出入口 |

---

### main.py — 应用入口

```python
def _init_state() -> None
```
初始化 `st.session_state` 默认键，并通过 URL `?token=xxx` 自动恢复登录状态（页面刷新后无需重新输入）。Token 过期时自动清除 URL 参数。

```python
def render_auth_page() -> None
```
未登录时渲染登录/注册页（两个并列 Tab），登录成功后写入 URL token 并 rerun。

```python
def main() -> None
```
应用主函数：`ensure_dirs()` → `_init_state()` → 未登录显示登录页 → 已登录加载 DB 并渲染五个 Tab。

**Streamlit 会话状态（`st.session_state`）**

| 键名 | 类型 | 说明 |
|------|------|------|
| `user` | `dict \| None` | 当前登录的 user 记录 |
| `upload_key` | `int` | 递增计数器，保存后重置上传控件 |
| `pending_selected` | `str \| None` | 灵感墙当前选中的 `session_id` |
| `archived_selected` | `str \| None` | 已归档当前选中的 `session_id` |
| `shared_selected` | `str \| None` | 情侣空间当前选中的 `session_id` |

---

*本文档与代码同步维护。模块接口变更时，请同步更新本文件。*
