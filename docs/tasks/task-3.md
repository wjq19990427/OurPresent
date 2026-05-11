# Task 3: 删除旧 JSON 库迁移路径 + 清空当前数据

**类型**：cleanup（移除本地阶段过渡代码）
**Branch**：`codex/task-3`
**前置任务**：task-2 已合并（bcrypt 切换完成）

## 背景

task-2 把密码哈希切到 bcrypt 后，`data/database.db` 中现存的旧用户已无法登录，本地仅 fixture 价值。借此一并清掉 v2.2.0 引入的「启动时自动从 `data/db.json` 迁移到 SQLite」过渡代码——本地阶段已经全员落到 SQLite，不需要再为旧 JSON 留兼容口。

## 目标

让代码只认 SQLite 一种持久化形态：

- 启动路径中不再嗅探、读取、解析 `data/db.json`
- 不再保留「旧版纯 sessions 数组结构」自动兼容逻辑
- 当前 `data/database.db` 中的脏数据清空，重新作为空库出发
- `Assets/Pending/` 与 `Assets/Final/` 下的孤儿文件一并清理

## 改动范围

**许动**：

- `backend/infrastructure/database/db.py` 中所有与 `db.json` / 旧顶层结构兼容相关的分支
- `backend/config/settings.py` 中如果还有 `db.json` 路径常量，删除
- `backend/tests/` 中针对「旧 JSON 迁移」「纯 sessions 数组兼容」的用例：删除而非改写
- `data/database.db`：删除（启动时由 `load_db()` 自动重建空库）
- `Assets/Pending/*`、`Assets/Final/*` 下所有文件：删除（保留两个目录本身）
- `README.md` 第 43 行附近「旧版本如果仍有 `data/db.json`，启动时会自动迁移」一句删除
- `docs/api/infra_db.md` 中 `load_db()` 描述里涉及 JSON 迁移、纯数组兼容、损坏回退的 3 个 bullet

**不许动**：

- SQLite schema、表结构、`load_db()/save_db()` 公开签名
- `EMPTY_DB` 常量本身（空库初始化仍需要）
- `auth` / `couples` / `sessions` / `maintenance` 业务代码
- `CHANGELOG.md` 中 v2.2.0 历史条目（那是发布历史，不是当前行为）

## 接口约定

- `load_db()` / `save_db()` / `ensure_dirs()` 公开签名与返回结构完全不变
- `load_db()` 在 SQLite 文件不存在时仍负责初始化空 schema；这一条保留
- 删除后 `load_db()` 不应再有任何 `os.path.exists("data/db.json")` 或等价分支
- 文件读取异常的兜底：若仍有必要保留 try/except，只能围绕 SQLite 自身的 IO 错误，不能为已不存在的 JSON 通路保留

## 验收行为（用户视角）

执行清理后再次启动：

- `rm -rf data/database.db Assets/Pending/* Assets/Final/*` 之后跑 `uv run streamlit run main.py`，应用正常启动，进入登录页
- 注册新用户 → 登录成功；DB 中只有新建的这一条用户
- 即使手工塞一个 `data/db.json` 到项目根目录的 `data/` 下，重启应用也不会把里面的内容导入 SQLite（已无该路径）
- 仓库根目录 `grep -ri "db\.json" backend/ frontend/ main.py` 应只剩注释/文档以外的零命中（或彻底零命中）

自动化检查：

- `uv run python -c "import backend, frontend; print('OK')"`
- `uv run pytest` 全绿（删除 JSON 迁移相关用例后剩余测试仍需通过）
- `uv run ruff check .` 无错

## 必读契约

- `docs/api/infra_db.md`（`load_db()` 当前描述包含 3 条需要删除的 bullet）

## 文档同步

- `docs/api/infra_db.md` 中 `load_db()` 描述同步精简
- `README.md` 第 43 行的迁移提示删除
- `docs/STATUS.md` 不要碰（架构师维护）
- `CHANGELOG.md [Unreleased]` 不要碰（架构师维护）
