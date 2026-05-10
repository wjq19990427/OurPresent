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