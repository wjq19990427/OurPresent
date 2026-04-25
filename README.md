# OurPresent 💝

> "不要以遗憾为代价去学会爱，愿我们能保留每一份感情中的美好。"

**OurPresent** 是一款专为情侣打造的私密记忆空间与智能情感辅助 Agent。这个项目脱胎于个人记录工具 MyPresent（在此特别鸣谢好友“鳄霸”提供的核心灵感，以及他口头技术入股的“5%原始股”）。它不仅是一个用于存放双方日常照片与碎碎念的加密双人空间，更是一个绝对忠诚、带有善意的“数字中间人”，旨在帮助情侣跨越沟通的屏障，更好地经营亲密关系。

### 💡 为什么叫 OurPresent？

与 MyPresent 一脉相承，"Present" 在这里同样寄托了我们对亲密关系的美好期许：

* **我们的当下 (Our Present):** 抛开过去的纠葛与未来的焦虑，感情最真实的状态就在此刻的相处中。无论是满心欢喜，还是那些难以当面直言的委屈与抱怨，在属于两人的空间里记录下来，本身就是一种情绪的沉淀。
* **共同的馈赠 (The Gift of Today):** 两个人能相遇并共同度过今天，本身就是上天最好的礼物。OurPresent 提醒我们活在当下，珍惜这段彼此陪伴的美好日常。
* **温柔地表达 (Present to You):** 当爱意太满或矛盾太僵，话到嘴边总是难以启齿。这里记录下的每一段文字与影像，最终都将化作一份延迟解锁的情感礼物，在时间沉淀后温柔地向对方敞开心扉（Present），让心意不再错位。

### 🚀 项目愿景

在日常相处中，女生往往需要闺蜜倾诉，男生也会向兄弟吐槽。但这些涉及两人隐私的情绪宣泄，往往伴随着信息外流的风险，甚至在不经意间激化矛盾。当我们真正遇到一个很爱的人时，常常因为不懂得如何表达、如何处理情绪，最终导致遗憾。

**OurPresent** 致力于成为一段亲密关系中“最完美的中间人”。

在基础体验上，它是一个绝对安全的情感防空洞。通过独特的“时间锁”与权限隔离机制，它能妥善保管那些当下不便直说的心事，给情绪一个缓冲期。

在智能化愿景上，项目计划深度融合大语言模型（LLM）与 RAG（检索增强生成）等前沿技术。通过将情侣间沉淀的图文日常、情绪标签进行私有化的向量结构化处理，OurPresent 能够代入双方视角，在绝对保护隐私的前提下生成客观温暖的相处总结。它不会泄露单方的秘密，却能敏锐地捕捉到情感的暗流，温柔地化解误会，引导双方看见彼此真正的需求。

我们都在学着去爱人。OurPresent 的终极目标，就是用技术的温度，守护每一份双向奔赴的真心。

# OurPresent — 情侣专属情感交互空间

本地运行的情侣双人情感记录工具，基于 **Streamlit** 构建。在保护个人绝对隐私的前提下，通过"延时共享"机制沉淀情感——你的记录只属于你自己，满 90 天后才能让对方看见。支持多用户注册与情侣绑定、权限状态机（时间锁）、分手协议与数据冻结销毁，并为后期接入 AI 智能体（RAG）预留了完整的接口边界。

> 基于 [MyPresent v2.1.0](../MyPresent) 重构演进，三层模块化架构。

---

## 目录

- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [数据模型](#数据模型)
  - [顶层结构](#顶层结构)
  - [User 记录](#user-记录)
  - [Couple 记录](#couple-记录)
  - [Session 记录](#session-记录)
- [核心接口（函数 API）](#核心接口函数-api)
  - [db.py — 数据层](#dbpy--数据层)
  - [auth.py — 鉴权层](#authpy--鉴权层)
  - [app.py — UI 渲染层](#apppy--ui-渲染层)
- [UI 页面说明](#ui-页面说明)
- [权限状态机详解](#权限状态机详解)
- [分手协议详解](#分手协议详解)
- [扩展开发指南](#扩展开发指南)
- [第二阶段接口预留](#第二阶段接口预留)

---

## 快速开始

**安装依赖**（国内镜像）

```bash
pip install streamlit opencv-python Pillow -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**启动应用**

```bash
cd D:\OurPresent
python -m streamlit run app.py
```

浏览器访问 `http://localhost:8501`。

**首次使用流程**

1. 双方各自在注册页创建账号（用户名 + 密码）
2. 注册成功后，页面显示各自的 **用户 ID**（形如 `usr_a1b2c3d4`）
3. 一方在「⚙️ 账户」页输入对方的用户 ID，发送绑定请求
4. 另一方登录后在「⚙️ 账户」页确认请求，绑定完成
5. 之后可在各自的「🗂️ 记录舱」上传内容，在「💌 情侣空间」查看对方共享的记录

**运行环境**

| 项目 | 要求 |
|------|------|
| Python | 3.9+ |
| Streamlit | 1.28+（需支持 `use_container_width`） |
| opencv-python | 4.x（视频缩略图，可选） |
| Pillow | 9.x+（图片处理，可选） |

> `opencv-python` 和 `Pillow` 未安装时，预览功能降级为文字提示，其余功能不受影响。

---

## 项目结构

```
D:\OurPresent\
├── app.py              # UI 层：全部 Streamlit 页面渲染
├── auth.py             # 鉴权层：注册/登录/情侣绑定/解绑协议
├── db.py               # 数据层：磁盘 I/O、状态机、数据销毁
├── CHANGELOG.md        # 版本更新记录
├── README.md           # 本文件
├── data/
│   └── db.json         # 统一数据库（自动生成）
└── Assets/
    ├── Pending/        # 待处理文件存储目录
    │   └── {session_id}_{index:03d}_{original_name}
    └── Final/          # 已归档文件存储目录
        ├── {session_id}_{index:03d}_{original_name}
        └── {session_id}.md     # 每条归档记录的 Markdown 文档
```

**文件命名规则**

与 MyPresent 保持一致，以 `session_id`（`YYYYMMDD_HHMMSS`）为前缀，同批文件用三位数字索引区分：

```
20260424_192301_000_photo.jpg
20260424_192301_001_note.txt
```

**三层架构关系**

```
app.py  ──调用──▶  auth.py  ──调用──▶  db.py  ──读写──▶  data/db.json
  │                                      │
  └──────────────直接调用────────────────┘
```

`auth.py` 不直接操作 `st.session_state`；`db.py` 不感知 Streamlit。后期前后端分离时，`db.py` 可直接复用为后端数据访问层。

---

## 数据模型

所有数据存储在 `data/db.json`，顶层为对象，包含三张表。

### 顶层结构

```jsonc
{
  "users":   [ /* User 记录列表 */ ],
  "couples": [ /* Couple 记录列表 */ ],
  "sessions": [ /* Session 记录列表 */ ]
}
```

---

### User 记录

```jsonc
{
  "user_id":       "usr_a1b2c3d4",          // 唯一 ID，注册时由 UUID4 前 8 位生成
  "username":      "Alice",                 // 用户名，2-20 字符，唯一
  "password_hash": "e3b0c44298fc1c14...",   // SHA-256(固定盐 + 密码)
  "couple_id":     "cp_12345678",           // 所属情侣关系 ID，未绑定时为 null
  "joined_at":     "2026-01-01 12:00:00"
}
```

---

### Couple 记录

```jsonc
{
  "couple_id":             "cp_12345678",
  "user_a":                "usr_a1b2c3d4",   // 发起绑定请求的一方
  "user_b":                "usr_e5f6g7h8",   // 收到请求的一方
  "created_at":            "2026-01-01 12:00:00",

  // 关系状态
  // "pending_bind" ─▶ "active" ─▶ "frozen" ─▶ "dissolved"
  "couple_status":         "active",

  // 解绑相关（active 时均为 null / false）
  "uncouple_initiated_by": null,             // 发起分手的 user_id
  "uncouple_initiated_at": null,             // 分手触发时间
  "both_agreed_uncouple":  false,            // 是否双方同意立即销毁
  "freeze_ends_at":        null              // 冻结到期时间，到期自动销毁数据
}
```

**`couple_status` 状态流转**

```
pending_bind  ──对方接受──▶  active  ──单方发起──▶  frozen  ──到期/双方同意──▶  dissolved
             ──对方拒绝──▶  (删除)
```

---

### Session 记录

```jsonc
{
  // ── 系统字段 ──────────────────────────────────────────────────────────
  "session_id":          "20260424_192301",    // 唯一 ID，格式 YYYYMMDD_HHMMSS
  "user_id":             "usr_a1b2c3d4",       // 创建者
  "couple_id":           "cp_12345678",        // 所属情侣关系，未绑定时为 null
  "status":              "pending",            // "pending" | "final"
  "upload_time":         "2026-04-24 19:23:01",
  "archive_time":        "",                   // 归档时填入，否则为 ""
  "is_complete":         false,                // 所有必填项是否已填，自动计算
  "edit_history":        [],                   // 仅 Final 记录追加

  // ── 可见性状态机（时间锁）────────────────────────────────────────────
  // "private" ─▶ "pending_unlock" ─▶ "shared"
  "visibility":          "private",
  "unlock_requested_at": null,                 // 用户申请共享时写入时间戳
  "shared_at":           null,                 // 满足 90 天条件后自动写入

  // ── 文件列表 ──────────────────────────────────────────────────────────
  "files": [
    {
      "filename":      "20260424_192301_000_photo.jpg",
      "original_name": "photo.jpg",
      "path":          "Assets/Pending/20260424_192301_000_photo.jpg"
    }
  ],
  "source_type": "file",                       // "file" | "text"

  // ── 元数据字段（由 FIELD_SCHEMA 驱动）────────────────────────────────
  "content_time": "2025-06-01",
  "description":  "描述内容",                  // 文件型记录强制必填（RAG 语料）
  "feeling":      "感受",
  "reason":       "",

  // ── 评论区 ────────────────────────────────────────────────────────────
  "comments": [
    {
      "id":         "20260425_100000_123456",
      "author":     "usr_a1b2c3d4",            // 评论者 user_id
      "text":       "评论内容",
      "created_at": "2026-04-25 10:00:00"
    }
  ]
}
```

### edit_history 条目结构

与 MyPresent 保持一致：

```jsonc
{
  "edited_at": "2026-04-25 10:00:00",
  "changes": {
    "feeling": { "from": "旧感受", "to": "新感受" }
  }
}
```

---

## 核心接口（函数 API）

### db.py — 数据层

#### 常量与配置

```python
BASE_DIR    = Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
DB_PATH     = DATA_DIR / "db.json"
ASSETS_DIR  = BASE_DIR / "Assets"
PENDING_DIR = ASSETS_DIR / "Pending"
FINAL_DIR   = ASSETS_DIR / "Final"
TEXT_EXTS   = {".txt", ".md"}           # 纯文字扩展名集合
```

**`FIELD_SCHEMA`** 与 MyPresent 用法完全相同，新增了对 `description` 的 `required=True` 标记。详见 MyPresent README「字段定义接口」章节。

---

#### 数据库操作

```python
def load_db() -> dict
```
读取 `data/db.json`，返回包含 `users`、`couples`、`sessions` 三个列表的字典。文件不存在或损坏时返回空结构。自动兼容 MyPresent 的纯数组格式。

---

```python
def save_db(data: dict) -> None
```
全量写入 `data/db.json`（UTF-8，中文不转义，缩进 2）。

---

```python
def load_db_with_tick() -> dict
```
加载 DB 并推进状态机（时间锁 + 冻结期检查）。**UI 层应始终调用此函数**，而非裸调 `load_db()`。

---

```python
def ensure_dirs() -> None
```
确保 `data/`、`Assets/Pending/`、`Assets/Final/` 目录存在，应在应用启动时调用。

---

#### 状态机推进

```python
def tick(db: dict) -> bool
```
在已加载的 `db` 对象上原地推进两类状态，有变化时返回 `True`：

1. **时间锁**：`visibility == "pending_unlock"` 且 `upload_time` 距今 ≥ 90 天 → 推进至 `"shared"`，写入 `shared_at`
2. **冻结期到期**：`couple_status == "frozen"` 且 `freeze_ends_at ≤ now()` → 调用 `destroy_couple_data()`

---

#### 用户 CRUD

```python
def create_user(username: str, password: str) -> dict
```
创建新用户并写入 DB，返回 user 记录。调用方需先确保 `username` 唯一（由 `auth.register()` 负责校验）。

---

```python
def get_user_by_username(username: str) -> dict | None
def get_user_by_id(user_id: str) -> dict | None
```

---

```python
def verify_password(user: dict, password: str) -> bool
```
校验用户密码（SHA-256 哈希比对）。

---

#### 情侣绑定 CRUD

```python
def send_couple_request(from_user_id: str, to_user_id: str) -> dict
```
创建 `couple_status = "pending_bind"` 的 couple 记录，返回该记录。

---

```python
def get_couple_for_user(user_id: str) -> dict | None
```
返回该用户当前有效的 couple 记录（`pending_bind` / `active` / `frozen`），不返回已解散的关系。

---

```python
def get_pending_requests_for_user(user_id: str) -> list[dict]
```
返回目标为该用户且状态为 `pending_bind` 的请求列表。

---

```python
def accept_couple_request(couple_id: str) -> None
```
接受绑定：`couple_status` → `"active"`，双方 user 记录的 `couple_id` 字段更新。

---

```python
def reject_couple_request(couple_id: str) -> None
```
拒绝绑定：从 DB 中删除该 couple 记录。

---

#### 解绑协议

```python
def initiate_uncouple(user_id: str) -> None
```
单方发起分手。`couple_status` → `"frozen"`，记录发起方和到期时间（90 天后）。

---

```python
def agree_uncouple(user_id: str) -> None
```
对方确认解绑。标记 `both_agreed_uncouple = True` 后立即调用 `destroy_couple_data()`。

---

```python
def destroy_couple_data(couple_id: str) -> None
```
**不可逆操作。** 删除该情侣关系下的全部 sessions 及对应文件，`couple_status` → `"dissolved"`，双方 user 的 `couple_id` 置 `null`。

---

#### Session 生命周期

与 MyPresent 的同名函数语义一致，新增 `user_id` 和 `couple_id` 参数：

```python
def save_session_pending(
    user_id: str,
    couple_id: str | None,
    file_data_list: list[tuple[bytes, str]],
    source_type: str,
    field_values: dict,
) -> None
```

```python
def save_session_final(
    user_id: str,
    couple_id: str | None,
    file_data_list: list[tuple[bytes, str]],
    source_type: str,
    field_values: dict,
) -> None
```

```python
def move_to_final(session_id: str) -> None
def update_session_fields(session_id: str, new_values: dict) -> None
```

---

#### 可见性控制

```python
def request_unlock(session_id: str) -> None
```
将 `visibility` 从 `"private"` 推进至 `"pending_unlock"`，记录 `unlock_requested_at`。

---

```python
def revoke_unlock(session_id: str) -> None
```
将 `visibility` 从 `"pending_unlock"` 退回至 `"private"`，清除 `unlock_requested_at`。

---

#### 数据导出

```python
def collect_export_files(user_id: str) -> list[Path]
```
返回该用户可导出的文件路径列表（仅 `session.user_id == user_id` 的文件）。冻结期内由 UI 层调用后打包为 ZIP。

---

#### 评论操作

与 MyPresent 相同，新增 `author_id` 参数：

```python
def add_comment(session_id: str, author_id: str, text: str) -> None
def delete_comment(session_id: str, comment_id: str) -> None
```

---

#### 字段校验

```python
def validate_session(session: dict) -> list[str]
def _is_text_session(session: dict) -> bool
```

用法与 MyPresent 完全相同。纯文字记录时 `description` 自动从必填列表中豁免。

---

### auth.py — 鉴权层

所有函数在失败时抛出对应异常，不返回错误码：

| 异常类 | 用于 |
|--------|------|
| `AuthError` | 注册/登录失败 |
| `CoupleError` | 情侣绑定/解绑操作失败 |

---

```python
def register(username: str, password: str) -> dict
```
注册校验：用户名 2-20 字符，密码 ≥ 6 位，用户名不重复。通过后调用 `db.create_user()`。

---

```python
def login(username: str, password: str) -> dict
```
登录校验：用户名存在且密码匹配。返回 user 记录。

---

```python
def send_bind_request(from_user_id: str, to_user_id: str) -> dict
```
发送绑定请求前的业务校验：不能向自己发送、目标用户存在、双方均无其他活跃或冻结关系。

---

```python
def accept_bind(couple_id: str) -> None
def reject_bind(couple_id: str) -> None
```

---

```python
def start_uncouple(user_id: str) -> None
def confirm_uncouple(user_id: str) -> None
```

---

```python
def can_view_session(session: dict, viewer_id: str) -> bool
```
**视图权限核心函数。** 创建者始终可见；情侣对方仅在 `visibility == "shared"` 时可见；其他用户不可见。

---

```python
def is_frozen(user_id: str) -> bool
```
判断当前用户所在关系是否处于冻结期，供 UI 层决定是否禁用写操作。

---

### app.py — UI 渲染层

#### Streamlit 会话状态

| 键名 | 类型 | 说明 |
|------|------|------|
| `user` | `dict \| None` | 当前登录的 user 记录，`None` 表示未登录 |
| `upload_key` | `int` | 递增计数器，保存后重置上传控件 |
| `pending_selected` | `str \| None` | 灵感墙当前选中的 `session_id` |
| `archived_selected` | `str \| None` | 已归档页当前选中的 `session_id` |
| `shared_selected` | `str \| None` | 情侣空间当前选中的 `session_id` |

---

```python
def render_field_inputs(prefix, defaults=None, skip_keys=None) -> dict
```
与 MyPresent 用法相同，必须在 `with st.form():` 块内调用。

---

```python
def render_comments(session: dict) -> None
```
必须在 `st.form` 外部调用。渲染评论列表（含评论者用户名）、删除按钮、新评论输入框。

---

```python
def render_card(col, session: dict, state_key: str) -> None
```
在 `st.columns` 对象中渲染 session 卡片，新增可见性状态徽章（🔒 / ⏳ / ✅）。

---

```python
def render_detail(session: dict, mode: str, read_only: bool = False) -> None
```

| `mode` | `read_only` | 说明 |
|--------|-------------|------|
| `"pending"` | `False` | 可编辑，支持暂存和归档 |
| `"final"` | `False` | 可编辑，保存时追加 edit_history |
| `"final"` | `True` | 冻结期只读；或查看对方共享内容 |
| `"shared"` | `True` | 情侣空间，始终只读 |

自己的记录在详情区显示可见性控制按钮（申请共享 / 撤回申请）。

---

## UI 页面说明

### Tab 1 — 🗂️ 记录舱（上传）

与 MyPresent Tab 1 功能相同，新增冻结期判断：冻结期内显示警告并跳过全部上传逻辑。

### Tab 2 — 🖼️ 灵感墙（待处理）

仅展示 `user_id == 当前用户` 且 `status == "pending"` 的记录。卡片新增可见性状态徽章。

### Tab 3 — 📚 已归档

仅展示 `user_id == 当前用户` 且 `status == "final"` 的记录。在详情区可操作时间锁（申请/撤回共享）。

### Tab 4 — 💌 情侣空间

展示伴侣 `visibility == "shared"` 的记录，调用 `can_view_session()` 二次验权。全部只读，可发表评论。未绑定时显示引导提示。

### Tab 5 — ⚙️ 账户

| 区块 | 内容 |
|------|------|
| 我的账户 | 展示用户名和用户 ID，退出登录 |
| 收到的绑定请求 | 列出 `pending_bind` 请求，逐条接受/拒绝 |
| 情侣关系 | 根据 `couple_status` 展示对应面板（见下） |

**情侣关系面板状态**

| `couple_status` | 展示内容 |
|-----------------|----------|
| 无关系 | 输入伴侣 ID 发送绑定请求 |
| `pending_bind` | 等待对方确认提示 |
| `active` | 已绑定信息 + 解绑协议入口 |
| `frozen` | 冻结期倒计时 + 数据导出入口 |

---

## 权限状态机详解

```
创建记录
  │
  ▼
[private]  ←──────── 撤回申请
  │
  │ 用户手动点击「申请共享」
  ▼
[pending_unlock]
  │
  │ db.tick() 检查：
  │ now() - upload_time ≥ 90 天
  ▼
[shared]  ──▶ 对方在「情侣空间」可见
```

**关键约束**

- 解锁等待基于 `upload_time`（内容创建时间），而非 `unlock_requested_at`（申请时间）
- 无法通过提前申请来绕过 90 天限制
- `pending_unlock` 阶段可随时撤回，不影响 90 天计时（下次重新申请后，已过去的时间仍然计入）

---

## 分手协议详解

### 单方发起（`start_uncouple`）

```
触发 initiate_uncouple()
  │
  ├─ couple_status → "frozen"
  ├─ 记录 uncouple_initiated_by, uncouple_initiated_at
  └─ freeze_ends_at = now() + 90天

冻结期内：
  ├─ 全局只读（is_frozen() == True）
  ├─ 双方均可导出自己的文件（collect_export_files）
  └─ db.tick() 到期 → destroy_couple_data() → couple_status = "dissolved"
```

### 双方同意（`confirm_uncouple`）

```
触发 agree_uncouple()
  │
  └─ 立即调用 destroy_couple_data()
       ├─ 删除全部 sessions（过滤 couple_id）
       ├─ 删除对应磁盘文件和 .md 文件
       └─ 双方 user.couple_id → null
```

### 数据导出规则

导出仅包含：
- `session.user_id == 当前用户` 的所有 session 的文件
- 不包含对方记录、双方共同生成的报告（第二阶段智能体产出）

---

## 扩展开发指南

### 1. 新增元数据字段

在 `db.py` 的 `FIELD_SCHEMA` 中追加字典，无需修改其他代码（与 MyPresent 完全相同）：

```python
{
    "key":         "location",
    "label":       "所在地",
    "required":    False,
    "type":        "text",
    "placeholder": "这段记忆发生在哪里？",
    "help":        "选填",
},
```

### 2. 替换密码哈希方案

生产环境应替换 `db.py` 中的 `_hash_password()`：

```python
import bcrypt

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(user: dict, password: str) -> bool:
    return bcrypt.checkpw(password.encode(), user["password_hash"].encode())
```

### 3. 接入外部存储

替换以下函数即可切换存储后端（与 MyPresent 相同）：

| 函数 | 当前行为 | 替换方向 |
|------|----------|----------|
| `load_db()` | 读本地 JSON | 查询关系数据库 / NoSQL |
| `save_db()` | 写本地 JSON | 写入数据库 |
| `_write_files()` | 写本地文件 | 上传到 OSS / S3 |
| `move_to_final()` | 本地 `shutil.move` | 远程 copy + delete |

### 4. 前后端分离迁移

Demo 阶段的 Streamlit 全栈架构迁移路线：

1. `db.py` → 直接作为后端数据访问层（FastAPI / Flask 调用）
2. `auth.py` → 封装为 `/register`、`/login`、`/couple/*` REST 接口
3. Session 可见性和权限检查（`can_view_session`）移至后端，前端不做权限判断
4. `app.py` → 替换为独立前端（React / Vue），通过 API 通信

### 5. 添加定时任务（生产环境）

当前 `db.tick()` 依赖页面加载触发。生产环境建议改为独立定时任务：

```python
# cron_worker.py（每小时执行一次）
from db import load_db, save_db, tick

if __name__ == "__main__":
    db = load_db()
    if tick(db):
        save_db(db)
```

配合 `crontab` 或 `APScheduler` 定期运行，确保冻结期到期时及时销毁数据。

---

## 第二阶段接口预留

第一阶段已为 AI 智能体接入预留了以下边界：

### RAG 向量化接口

每条 Session 包含以下可作为 Chunk + Metadata 的字段：

| 字段 | RAG 用途 |
|------|----------|
| `description` | 主要文本 Chunk（强制必填，保证语料质量） |
| `feeling` | 情感 Metadata |
| `content_time` | 时间 Metadata |
| `visibility` | 检索过滤条件（**只允许检索 `shared` 状态的记录**） |
| `couple_id` | 关系域隔离 |
| `user_id` | 作者标识 |
| `shared_at` | 共享时间 Metadata |

**过滤规则（定期情感周报 Agent 必须遵守）**：

```python
rag_chunks = [
    s for s in db["sessions"]
    if s.get("couple_id") == target_couple_id
    and s.get("visibility") == "shared"
]
```

### 智能体模块预留函数（待实现）

在 `db.py` 末尾预留以下函数签名，第二阶段实现：

```python
def get_shared_sessions_for_rag(couple_id: str) -> list[dict]:
    """返回指定情侣关系下所有 visibility=="shared" 的 sessions，供 RAG 索引。"""
    ...

def get_report_history(couple_id: str) -> list[dict]:
    """返回该情侣的历史周报记录（第二阶段新增 reports 表）。"""
    ...
```

### 中立助手 System Prompt 约束（备忘）

实时情感助手接入时，System Prompt 需包含以下约束（NVC 框架）：

- 禁止对双方行为做对错判断
- 回复格式强制遵循「观察 → 感受 → 需要 → 请求」四步结构
- 仅允许引用 `visibility == "shared"` 的数据，不得访问私密记录
- 不得在回复中具体引用对方记录的原文（防止隐私泄露）
