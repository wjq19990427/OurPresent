# Task 4: 自定义共享开放时间（替代固定 90 天）

**类型**：feature（打破固定时间锁）
**Branch**：`codex/task-4`
**前置任务**：无

## 背景

当前 `pending_unlock → shared` 的推进硬编码为「上传满 90 天」（`backend/application/maintenance/ticking.py`）。产品定位上「延时表达」是核心叙事，但 90 天的固定时长让用户没有选择权。本任务让用户在申请共享时自己定「何时对伴侣开放」，时间锁仍在，灵活度交回用户。

## 目标

- 用户申请共享时显式指定 `unlock_at`（目标解锁时刻）
- 提供预设档位 UI + 日历自由选 + 「立即」按钮
- 时间锁推进逻辑从「`upload_time + 90 天`」改为「`session.unlock_at <= now`」
- 旧硬编码 90 天逻辑彻底删除（不保留兼容分支）

## 改动范围

**许动**：

- `backend/domain/models/session.py`（`SessionRecord` 新增 `unlock_at` 字段）
- `backend/infrastructure/database/sessions_repo.py`（SQLite schema 增列、读写同步）
- `backend/infrastructure/database/db.py`（如有相关 schema 初始化处需同步）
- `backend/application/sessions/sharing.py`（`request_unlock` 签名扩展）
- `backend/application/sessions/destruction.py` / `editing.py` 等若有读取/写入 `unlock_at` 的副作用，按需同步
- `backend/application/maintenance/ticking.py`（推进规则改为基于 `unlock_at`）
- `backend/config/settings.py`（如出现固定 90 这一常量，删除）
- `frontend/streamlit_app/`（申请共享入口的 UI 改造）
- `backend/tests/`（覆盖新档位与「立即」分支）

**不许动**：

- `status` 字段流程（`pending` / `final`）
- `visibility` 状态机的其他迁移路径（`private` ↔ `pending_unlock`，`shared` 终态）；本任务只改「`pending_unlock → shared`」的触发条件
- `couples` / `auth` / `tokens` / `maintenance` 中冻结期与 token 清理逻辑
- `revoke_unlock` 行为（仅同步处理 `unlock_at` 清空，无需扩展语义）

## 接口约定

- `SessionRecord` 新增 `unlock_at: str | None`，格式与 `now_str()` 一致（`%Y-%m-%d %H:%M:%S`）
- `request_unlock(session_id: str, unlock_at: str) -> None`：
  - `unlock_at` 必填，无默认值（默认值由前端决定）
  - 行为：`visibility → "pending_unlock"`，写入 `unlock_requested_at = now`、`unlock_at = 传入值`
  - 若 `unlock_at <= now`（即「立即」档），直接进 `shared`，写入 `shared_at = now`，不经过 `pending_unlock` 中间态
- `revoke_unlock(session_id)`：清空 `unlock_requested_at` **和** `unlock_at`
- `tick()`：判定改为 `session.unlock_at is not None and parse_dt(session.unlock_at) <= now`，命中则推进为 `shared`，写入 `shared_at`；不再读取 `upload_time` 计算 90 天
- 「档位」是纯 UI 概念，下层（application / repo / tick）只接受具体的 `unlock_at` 字符串

## 预设档位（UI 规约）

申请共享入口提供以下选项，最终全部转换为 `unlock_at` 字符串后调用 `request_unlock`：

- **立即**（`unlock_at = now`）
- **1 天后**
- **3 天后**
- **1 周后**（**默认选中**）
- **1 个月后**
- **90 天后**
- **自定义日期**（日历组件，最小可选 = 今天；选今天等同「立即」）

时间换算以「申请共享按钮被按下」的瞬间为锚点。

## 数据兼容

- 库 schema 新增 `unlock_at` 列，旧记录该列为空字符串或 NULL（实现工自决，但 `from_dict` 必须能容忍空值）
- 若库里已有 `visibility="pending_unlock"` 的历史 session 但 `unlock_at` 为空：本任务不做回填，由 task-5 的「修改 unlock_at」流程让用户自行处理
- 测试 fixture 中所有构造 `pending_unlock` 状态的用例必须显式给出 `unlock_at`

## 验收行为（用户视角）

启动 `uv run streamlit run main.py` 跑通：

- 新建 session → 申请共享 → 默认选中「1 周后」→ DB 中 `unlock_at = now + 7 天`，`visibility = pending_unlock`
- 选「立即」→ 该 session 直接进 `shared`，伴侣在「💌 情侣空间」立即可见
- 选「1 个月后」→ `unlock_at = now + 30 天`，月内不可见
- 选「自定义日期」→ 打开日历，最小可选今天；选未来日期 → `unlock_at` 写入；选今天 → 等同「立即」
- 申请共享后立即调用 `tick()`，若 `unlock_at > now`，session 保持 `pending_unlock`；若 `unlock_at <= now`，进入 `shared`
- 撤回共享 → `visibility = private`，`unlock_requested_at` 和 `unlock_at` 均清空
- 伴侣在 `pending_unlock` 期间始终看不到该 session

自动化检查：

- `uv run python -c "import backend, frontend; print('OK')"`
- `uv run pytest` 全绿，且新增覆盖：默认 1 周、立即、自定义未来日期、tick 推进、revoke 清空 `unlock_at`
- `uv run ruff check .` 无错

## 已知陷阱

- `tick()` 在 `load_db_with_tick()` 中按整库扫描，新规则不能改变性能特征
- `upload_time` / `unlock_requested_at` / `unlock_at` / `shared_at` 四个时间字段的语义边界要在 `domain_models.md` 描述清楚，避免后续误用
- 「立即」走的是 `request_unlock` 内部短路，而非「申请 + 紧接着 unlock_now」两步——确保 DB 中不会留下「pending_unlock 且 unlock_at <= upload_time」的中间快照

## 必读契约

- `docs/api/domain_models.md`（SessionRecord 字段全集）
- `docs/api/app_sessions.md`（sharing 当前签名）
- `docs/api/app_maintenance.md`（tick 当前 90 天规则）
- `docs/api/infra_db.md`（sessions_repo 当前列）
- `docs/api/frontend_streamlit.md`（申请共享 UI 当前形态）

## 文档同步

以上 5 份 L2 契约均需同步本任务的字段、签名与行为变化。L2 契约更新视为本任务的一部分，未更新不算完成。`docs/STATUS.md` 与 `CHANGELOG.md` 不动（架构师维护）。
