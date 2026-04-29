# Changelog

所有版本的功能修改和更新记录。版本号格式：`主版本.次版本.补丁`。

---

## [v2.0.0] - 2026-04-30

### 重构（无新功能）

**代码目录结构拆分**：将原有 `app.py` + `db.py` + `auth.py` 三文件架构，按职责拆分为以下模块：

```
core/
  config.py          # 路径常量、TEXT_EXTS、TOKEN_EXPIRE_HOURS、FIELD_SCHEMA
  state_machine.py   # tick()、load_db_with_tick()
  agent_skills.py    # Phase 2 LLM 接口占位

utils/
  validators.py      # _is_text_session()、validate_session()
  file_processor.py  # write_files()、video_thumbnail()、pil_to_png_bytes()

backend/
  db_manager.py      # JSON 读写、User/Couple CRUD、登录 Token 管理
  session_manager.py # Session 生命周期、评论、可见性控制、数据销毁、解绑协议
  auth_manager.py    # 注册/登录/绑定业务校验（AuthError、CoupleError）

frontend/
  components.py      # 会话工具、显示辅助、字段渲染、卡片、详情区、评论区
  pages/
    tab_upload.py    # Tab 1 — 记录舱
    tab_pending.py   # Tab 2 — 灵感墙
    tab_final.py     # Tab 3 — 已归档
    tab_shared.py    # Tab 4 — 情侣空间
    tab_account.py   # Tab 5 — 账户设置

main.py              # 入口：_init_state()、render_auth_page()、main()
```

**变更细节**

- 所有路径常量和 `FIELD_SCHEMA` 集中到 `core/config.py`，消除跨模块重复定义
- `_is_text_session` / `validate_session` 移至 `utils/validators.py`，可独立单元测试
- `_write_files` 重命名为 `write_files`（公开函数），与视频缩略图工具同移至 `utils/file_processor.py`
- `initiate_uncouple` / `agree_uncouple` / `destroy_couple_data` 从 `db.py` 移至 `backend/session_manager.py`，与 Session 生命周期管理统一
- `tick` / `load_db_with_tick` 单独提取为 `core/state_machine.py`，职责更清晰
- 原 `app.py` 中的 Tab 渲染函数各自独立为 `frontend/pages/tab_*.py`
- 入口由 `app.py` 改为 `main.py`，启动命令更新为 `python -m streamlit run main.py`
- 旧的 `app.py`、`db.py`、`auth.py` 保留（向后兼容），后续可删除

**依赖层次（无循环导入）**

```
core/config → utils → backend/db_manager → backend/session_manager
→ backend/auth_manager → core/state_machine → frontend → main.py
```

---

## [v1.2.0] - 2026-04-24

### 新增

- **持久化登录状态**：登录成功后在 `data/db.json` 的 `auth_tokens` 表写入 UUID token，并通过 `st.query_params["token"]` 将 token 写入 URL
  - 刷新页面时 `_init_state()` 读取 URL 中的 token 并自动校验恢复登录，无需重新输入账号密码
  - Token 默认有效期 **24 小时**，到期后刷新页面自动跳转至登录页
  - 退出登录时同步从 DB 中撤销 token 并清除 URL 参数
  - `db.tick()` 每次加载时自动清理所有已过期 token

- **两标签页测试兼容**：每个浏览器标签页拥有独立的 `st.session_state` 和 URL query param，Tab 1 登录用户 A、Tab 2 登录用户 B 互不干扰，行为与修改前完全一致

### 变更

- `data/db.json` 顶层新增 `auth_tokens` 数组，自动兼容旧格式（读取时若字段缺失则补全为空数组）
- `db._EMPTY_DB` 补充 `auth_tokens` 初始键

### 新增函数（`db.py`）

| 函数 | 说明 |
|------|------|
| `create_auth_token(user_id)` | 创建 token，写入 DB，返回 token 字符串 |
| `validate_auth_token(token)` | 校验 token 有效性，返回 user 记录或 None |
| `revoke_auth_token(token)` | 使 token 失效（退出登录时调用） |

---

## [v1.1.0] - 2026-04-24

### 修复

- **情侣绑定确认 UI 逻辑错误**：`pending_bind` 状态下，接收方和发送方共用同一段提示文案"等待对方确认中……"，导致接收方误以为无需操作，忽略上方的接受/拒绝按钮
  - 修复：区分发送方（`couple["user_a"] == 当前用户`）和接收方，分别展示不同提示
  - 发送方：显示"已向 XXX 发出绑定请求，等待对方确认……"
  - 接收方：显示醒目黄色警告"👆 请在上方「收到的绑定请求」区点击接受或拒绝"

---

## [v1.0.0] - 2026-04-24

### 新增（首个可运行版本）

**架构重构（基于 MyPresent v2.1.0 演进）**

- 从单人单文件架构重构为三层模块化架构：
  - `db.py`：数据层，负责所有磁盘 I/O 和状态机推进
  - `auth.py`：鉴权层，负责注册/登录/情侣绑定/解绑协议
  - `app.py`：UI 层，全部 Streamlit 页面渲染

**多用户系统**

- 注册/登录页（用户名 + 密码，SHA-256 哈希存储）
- 每位用户生成唯一 `user_id`（`usr_` + 8位 UUID hex）
- `data/db.json` 替换 `pending_db.json`，顶层从 JSON 数组升级为对象，包含 `users`、`couples`、`sessions` 三张表

**情侣绑定系统**

- 通过 `user_id` 搜索伴侣并发起绑定请求（`pending_bind` 状态）
- 被邀请方在「账户」页确认或拒绝，确认后状态升级为 `active`
- 绑定后双方共享同一 `couple_id`，数据按此字段关联

**权限状态机（时间锁）**

- Session 新增 `visibility` 字段，三态：`private` → `pending_unlock` → `shared`
- 创建时默认 `private`，仅创建者可见
- 用户手动申请共享：写入 `unlock_requested_at`，状态变为 `pending_unlock`
- `db.tick()` 在每次页面加载时运行：满 90 天后自动推进至 `shared`，写入 `shared_at`
- 支持在 `pending_unlock` 阶段撤回申请，恢复为 `private`

**分手协议与数据冻结**

- 单方发起解绑：`couple_status` 变为 `frozen`，记录 `freeze_ends_at`（90 天后）
- 冻结期内应用全局只读，上传/编辑入口均禁用
- `db.tick()` 到期自动调用 `destroy_couple_data()`，删除双方全部 sessions 和文件
- 双方同意解绑：调用 `agree_uncouple()`，立即销毁，无需等待冻结期
- 冻结期内支持数据导出：仅导出属于自己的文件，打包为 ZIP 下载

**数据隔离**

- 所有文件统一存放于 `Assets/Pending/` 和 `Assets/Final/`，不按用户分目录
- 数据层通过 `user_id` / `couple_id` 过滤，UI 层仅渲染当前用户的数据
- 情侣空间（Tab 4）仅展示伴侣 `visibility == "shared"` 的记录，调用 `can_view_session()` 二次校验

**强制文本描述（RAG 预备）**

- 文件型记录的 `description` 字段改为强制必填（`required=True`）
- 纯文字/文本文件记录保留自动填充逻辑，描述由内容自动写入
- Session 新增 `couple_id`、`user_id`、`visibility`、`unlock_requested_at`、`shared_at` 字段，为后期 RAG 向量化提供结构化 Metadata

**评论区扩展**

- 评论结构新增 `author` 字段，记录评论者 `user_id`
- 渲染时展示评论者用户名

**UI 新增 Tab**

- Tab 4「💌 情侣空间」：展示伴侣共享给自己的记录，只读查看
- Tab 5「⚙️ 账户」：用户信息、绑定请求收发、解绑协议、冻结期导出

### 变更

- `pending_db.json` 迁移为 `data/db.json`，顶层结构从数组变为对象
- `FIELD_SCHEMA` 中 `description` 的 `required` 字段从 `True`（仅文字必填）改为对所有 source_type 均必填；纯文字记录通过 `skip_keys` 机制绕过 UI 渲染，不破坏 Schema 定义
- Session `comments` 条目新增 `author` 字段（`user_id`）
- 文件存储路径 `Assets/` 目录结构不变，兼容 MyPresent 原有文件

### 已知限制

- `db.json` 为本地单文件，并发写入无锁保护，不适合多实例部署（Demo 阶段可接受）
- `db.tick()` 依赖页面加载触发，无独立定时任务；极端情况下冻结期到期但无人访问时不会立即销毁（安全方向保守，可接受）
- 密码哈希使用 SHA-256 + 固定盐，适合本地 Demo，生产环境应替换为 `bcrypt` 或 `argon2`
