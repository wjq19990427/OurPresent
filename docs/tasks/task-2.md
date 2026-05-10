# Task 2: 密码哈希切换到 bcrypt

**类型**：refactor（安全基线）
**Branch**：`codex/task-2`
**前置任务**：无（与 task-1 互不冲突，可并行）

## 目标

将用户密码哈希算法从 SHA-256 + 固定盐切换到 **bcrypt**（每用户独立盐 + 自适应代价因子）。仅替换算法，不改变 `register()` / `login()` 的对外契约。

## 改动范围

**许动**：

- `backend/application/auth/commands.py`（注册时的哈希、登录时的校验）
- 任何当前承载 SHA-256 计算的内部辅助（位置由实现工自行确定，可保留或合并）
- `pyproject.toml` 添加 `bcrypt` 依赖；运行 `uv lock` 同步
- `backend/tests/` 中如果有断言哈希值字面量或哈希算法的测试，相应调整

**不许动**：

- `User` dataclass 字段集合
- `application/auth/tokens.py` 与 `application/auth/errors.py`
- 数据库 schema（`password_hash` 列仍是字符串）
- `couples` / `sessions` / `maintenance` 子域

## 接口约定

- `register(username, password)` / `login(username, password)` 公开签名和异常行为不变
- `User.password_hash` 字段语义不变（仍是字符串），仅取值格式从 64 位 hex 变成 bcrypt 输出
- 算法选型固定为 **bcrypt**（`bcrypt` 库），不要选 argon2 或自实现 PBKDF2——选型理由：标准化、纯 Python 包装、无系统依赖

## 数据兼容

- 当前 `data/database.db` 中的旧用户视为开发期 fixture，**不需要兼容旧哈希、不需要写迁移逻辑**
- 实现工本地若有旧 DB 导致登录失败，删除 `data/database.db` 重建即可
- 不要保留「同时支持 SHA-256 和 bcrypt」的双轨逻辑

## 验收行为（用户视角）

- 注册新用户成功；DB 中 `password_hash` 不是 64 位 hex（即不是 SHA-256 输出）
- 用同一密码注册两个不同用户，两条 `password_hash` 不相等（独立盐验证）
- 用正确密码登录成功
- 用错误密码登录抛 `AuthError`
- 持久化登录 token 行为不受影响

自动化检查：

- `uv run python -c "import backend, frontend; print('OK')"`
- `uv run pytest` 全绿（auth 相关测试是关键，必须覆盖到 register + login + 错误密码路径）
- `uv run ruff check .` 无错

## 必读契约

- `docs/api/app_auth.md`（register / login / token 三组用例的当前行为）
- `docs/api/domain_models.md`（User 部分）

## 文档同步

- 若 `app_auth.md` 中描述了具体哈希算法（如「SHA-256 + 固定盐」），同步替换为 bcrypt
- 若仅描述行为契约（不涉及算法名），可不动
- `docs/STATUS.md` 不要碰（架构师维护）
