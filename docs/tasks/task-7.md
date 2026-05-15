# Task 7: 情感周报 · 数据模型与持久化

**类型**：feature（纯数据层 + 字段扩展，无业务逻辑）
**Branch**：`codex/task-7`
**前置任务**：无（task-6 已合并）
**所属模块**：Phase 2 · 情感周报第一步

## 背景

`docs/notes/weekly_report.md` 已确定情感周报设计。本任务铺设数据底座，让后续 task-8 / task-9 能在稳定的字段与表上施工。**本任务不引入任何业务逻辑、不接 LLM、不改 UI。**

## 目标

1. 新增 `Report` 领域模型
2. 新增 `reports` 表与对应 repository
3. `User` / `Couple` 各增一个字段承载服务开关与频率
4. `destroy_couple_data()` 联动删除 reports

## 改动范围

**许动**：

- `backend/domain/models/`：新增 `report.py`，扩展 `user.py` 与 `couple.py`
- `backend/infrastructure/database/db.py`：`_migrate_db` 增加新表与 ALTER；`load_db()/save_db()` 顶层字典扩展 `reports` 键
- `backend/infrastructure/database/`：新增 `reports_repo.py`
- `backend/application/couples/`：`destroy_couple_data` 调用链增加删除 reports 的步骤
- `backend/tests/`：补 reports_repo 与 destruction 联动的测试
- `docs/api/domain_models.md` / `docs/api/infra_db.md` / `docs/api/app_couple.md`：L2 契约同步
- 新增 `docs/api/app_reports.md`（仅写 Report 模型与 repository 部分，application 用例留给 task-8/9）

**不许动**：

- `frontend/**`（本任务不改 UI）
- `backend/application/sessions/*` / `auth/*` / `maintenance/*`
- `backend/infrastructure/ai/*`（task-9 才动）
- `docs/STATUS.md` / `CHANGELOG.md`（架构师维护）

## 接口约定

### `Report` 模型

新增 dataclass，字段与设计稿 `docs/notes/weekly_report.md` §3 一致：

- `report_id: str`（命名规则：`rpt_YYYYMMDD_<couple_id>`）
- `couple_id: str`
- `window_start: str` / `window_end: str`（与现有 `upload_time` 风格一致，`YYYY-MM-DD HH:MM:SS`）
- `generated_at: str`
- `model_version: str`（task-9 填入；本任务允许空串）
- `footprint: dict` / `weather: dict` / `resonance: list` / `suspense: list`
- `status: str`，取值 `"ready" | "failed" | "sparse"`
- `source_session_ids: list[str]`
- 提供 `from_dict()` / `to_dict()`，与 `User` / `Couple` / `SessionRecord` 风格一致

### `User` 新字段

- `weekly_report_enabled: bool`，默认 `False`
- 语义：当前用户是否开启情感周报服务
- 持久化：通过 `_migrate_db` ALTER 加列；旧数据读取时自动默认 `False`

### `Couple` 新字段

- `weekly_report_interval_days: int`，默认 `7`
- 语义：当前 couple 的周报间隔天数（双方共享配置）
- 取值范围由 task-8 在 UI 层约束，本任务不做校验

### `reports_repo`

公开签名（命名可微调，语义不可变）：

```python
def create_report(report: Report) -> None
def get_report(report_id: str) -> Report | None
def list_reports_for_couple(couple_id: str) -> list[Report]
def update_report(report: Report) -> None       # task-9 失败重试用
def delete_reports_for_couple(couple_id: str) -> int   # 返回删除条数，供 destruction 联动
```

- 行为对齐现有 `sessions_repo` / `couples_repo`：操作 SQLite，dict ↔ dataclass 严格收敛在 repository 边界
- `list_reports_for_couple` 按 `generated_at` 倒序

### `load_db()/save_db()` 与顶层字典

- `load_db()` 返回的字典新增顶层键 `reports`，值为 `list[dict]`
- `save_db()` 写回该键
- 旧数据兼容：首次启动时该键缺失则补全为空数组（与现有 `auth_tokens` 兼容模式一致）

### destruction 联动

- `application/couples/uncoupling.py` 的销毁链路（或当前实际承载销毁逻辑的入口）增加调用 `reports_repo.delete_reports_for_couple(couple_id)`
- 删除顺序由实现工决定，但必须保证整条销毁链事务语义不变弱

## 验收行为（用户视角）

由于本任务不改 UI，验收主要靠自动化：

- `uv run python -c "import backend; print('OK')"` 通过
- `uv run pytest` 全绿；其中新增测试覆盖：
  - 创建 Report 并读回内容一致
  - `list_reports_for_couple` 按 `generated_at` 倒序
  - 销毁 couple 后 `list_reports_for_couple` 返回空
  - 旧库（无 `reports` / 无新字段）启动后能正常 `load_db()` / `save_db()`
- `uv run ruff check .` 无错
- 首次启动后 `data/database.db` 的 `users` / `couples` 表多出新列，`reports` 表存在但为空

## 已知陷阱

- `_migrate_db` 的 ALTER TABLE 路径已有先例（task-4 引入 `unlock_at`）。新增列时务必为旧行填默认值；具体如何兼容旧数据由实现工读 `_migrate_db` 现有写法后决定
- 设计稿 §3 表里 `Report` 字段较多（4 个模块 + 元数据）。表结构是 JSON blob 单列还是拆分多列由实现工自决，但 repository 公开签名必须返回完整的 `Report` 对象——业务层不应感知存储形态
- `destroy_couple_data` 当前在 `application/couples` 还是 `application/sessions/destruction.py`，由实现工读现有代码确认入口
- 不要在本任务里实现 `generate_weekly_report` 或任何 LLM 调用——task-9 才动

## 必读契约

- `docs/api/domain_models.md`（现有 `User` / `Couple` / `SessionRecord` 形态与 `from_dict/to_dict` 风格）
- `docs/api/infra_db.md`（`load_db()/save_db()`、`_migrate_db`、repository 现有模式）
- `docs/api/app_couple.md`（destruction 现有链路）
- `docs/notes/weekly_report.md` §3 / §8（Report schema、destruction 联动要求）

## 文档同步

- `docs/api/domain_models.md`：新增 `Report` 章节，`User` / `Couple` 章节追加新字段
- `docs/api/infra_db.md`：新增 `reports_repo` 章节，`load_db()` 顶层字典补 `reports` 键
- `docs/api/app_couple.md` 或 `docs/api/app_sessions.md`（视实际入口）：destruction 章节补一句「同时删除该 couple 的所有 reports」
- 新建 `docs/api/app_reports.md`：仅写本任务落地的内容（Report 模型 + repository CRUD）；application 用例占位「task-8 / task-9 落地」
- `docs/ARCHITECTURE.md` §5 L2 契约表追加 `app_reports.md` 行
