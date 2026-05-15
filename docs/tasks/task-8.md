# Task 8: 情感周报 · metrics 与服务开关 UI

**类型**：feature（无 LLM 部分的完整骨架）
**Branch**：`codex/task-8`
**前置任务**：task-7 已合并

## 背景

task-7 已铺好数据底座。本任务把「不需要 LLM 的部分」全部落地：

- footprint / suspense 两个模块的结构化计算（纯 Python）
- 「设置」tab 的服务开关 UI 与双方启用判定
- 「我们」tab 的周报区位**占位**（未生成态文案 + 视服务状态条件渲染），不真渲染报告内容

完成后用户可以在「设置」里启用服务、看到对方开启状态、约定频率，但还没有真实周报生成（等 task-9）。

## 目标

1. 实现 `application/reports/metrics.py`：从一组 `SessionRecord` 与 window 计算 footprint 与 suspense
2. 实现 `application/reports/query.py`：`list_reports` / `get_report` 薄包装（基于 task-7 repo）
3. 「设置」tab 新增「情感周报服务」section（开关、对方状态、频率）
4. 「我们」tab 顶部加占位区：根据服务启用状态显示不同文案，未来 task-9/11 在此渲染真实报告

## 改动范围

**许动**：

- `backend/application/reports/`：新增 `metrics.py` / `query.py`
- `backend/application/reports/policies.py`（新增）：服务启用判定函数
- `frontend/streamlit_app/pages/tab_settings.py`：新增「情感周报服务」section
- `frontend/streamlit_app/pages/tab_us.py`：顶部增加周报占位区
- `frontend/streamlit_app/components.py`：若需要新 helper，可加
- `backend/tests/`：补 metrics 与 policies 的单元测试
- `docs/api/app_reports.md`：补 metrics / query / policies 章节
- `docs/api/frontend_streamlit.md`：补「设置」section 与「我们」占位区描述
- `docs/api/infra_ai.md`：`get_report_history` 占位改为薄包装委托 `query.list_reports`

**不许动**：

- `backend/infrastructure/ai/*` 中除 `agent_skills.py` 之外的文件（task-9 才动 llm_client）
- `backend/domain/models/*`（task-7 已经定型）
- 「我们」tab 中现有「shared 时间线」的过滤与排序逻辑（task-6 已固化）
- 「设置」中现有的账户 / 绑定 / 解绑 section
- `docs/STATUS.md` / `CHANGELOG.md`

## 接口约定

### `metrics.py`

输入是「该 couple 在 window 内的 shared sessions」+ window 自身。输出是符合设计稿 §3 schema 的两个 dict：

```python
def compute_footprint(sessions: list[SessionRecord], window: tuple[datetime, datetime]) -> dict
def compute_suspense(couple_id: str, now: datetime) -> list[dict]
```

- `compute_footprint` 字段对齐设计稿 §3：`total` / `by_kind` / `active_days` / `comment_count` / `by_author`
- `compute_suspense` 输入是当前时刻；返回该 couple 当前所有 `visibility == "pending_unlock"` 的 session 元数据列表（按 unlock_at 升序），字段对齐设计稿 §3
- 两个函数都是纯函数，不写库、不调外部服务
- `by_kind` 的「kind」从 session 的 `source_type` + 文件扩展名推导；具体 kind 字典（photo / video / text 等）按设计稿 §3 给出的三类做最小集

### `query.py`

```python
def list_reports(couple_id: str) -> list[Report]
def get_latest_ready_report(couple_id: str) -> Report | None
def get_report(report_id: str) -> Report | None
```

- 直接调 `reports_repo`，按 `generated_at` 倒序
- `get_latest_ready_report` 过滤 `status in {"ready", "sparse"}`（sparse 也算可见态）

### `policies.py`

```python
def service_active_for_couple(couple_id: str) -> bool
def partner_enabled_status(user_id: str) -> Literal["both", "only_self", "only_partner", "neither"]
```

- `service_active_for_couple`：couple 双方 `weekly_report_enabled` 都为 True 时返回 True；任一方未绑定 / 未开启则 False
- `partner_enabled_status`：从当前 user 视角描述自己与对方的开启组合，UI 据此选文案

### 「设置」tab 新增 section

- 标题：「情感周报服务」（具体 Streamlit 表达由实现工决定）
- 我的开关：绑定 `User.weekly_report_enabled`，切换立即持久化
- 对方状态：根据 `partner_enabled_status` 显示「✅ 对方已开启」/「⌛ 对方尚未开启」/「（未绑定伴侣）」
- 频率 dropdown：仅当 `service_active_for_couple == True` 时显示；选项 `7 / 14 / 30`；改动立即持久化到 `Couple.weekly_report_interval_days`
- 未绑定伴侣时：整个 section 显示但开关只影响自己；提示「绑定伴侣后两人都开启即可生效」

### 「我们」tab 周报占位区

顶部新增区域（位置：现有 shared 时间线之上），按服务状态条件渲染：

| 状态 | 展示 |
|------|------|
| 未绑定伴侣 | 不显示占位区 |
| 双方未开启 / 仅自己开启 | 显示邀请文案（具体措辞见设计稿 §5.1，由实现工敲定友好语气） |
| 仅对方开启 | 显示「对方已开启周报，要不要一起开启？」并引导到「设置」 |
| 双方都开启 + 尚无报告 | 显示「邀请你写下第一周的共享记录」 |
| 双方都开启 + 有报告 | 本任务**仅显示占位「周报功能开发中」**，task-11 才真实渲染 |

**本任务不调 metrics 也不显示真实数据**——只是把状态分支跑通，让 task-9/11 接管时 UI 入口已就位。

## 验收行为（用户视角）

`uv run streamlit run main.py`：

- 单用户未绑定伴侣 → 「设置」能看到「情感周报服务」开关；切换后刷新页面状态保持
- 两用户已绑定，仅 A 开启 → A 的「我们」顶部显示等待对方文案；B 的「我们」顶部显示邀请文案；双方设置里能正确看到对方状态
- 两用户都开启 → 双方设置里出现频率 dropdown；改动一方频率后，对方设置里也看到新频率（同 couple 字段）
- 关闭服务 → 「我们」占位区立刻回到邀请态
- 解绑后再绑定新伴侣 → 自己的 `weekly_report_enabled` 状态保留（个人偏好），但 `weekly_report_interval_days` 跟新 couple 走

自动化检查：

- `uv run python -c "import backend, frontend; print('OK')"`
- `uv run pytest`：新增覆盖
  - `compute_footprint` 在空 sessions / 单作者 / 双作者 / 多 kind 下结果正确
  - `compute_suspense` 按 unlock_at 升序，且只返回 pending_unlock
  - `service_active_for_couple` 在四种组合下结果正确
- `uv run ruff check .` 无错

## 已知陷阱

- 现有 `tab_settings.py` 由 task-6 改名自 `tab_account.py`，section 划分由实现工读现有结构后决定如何插入新 section
- `Couple.weekly_report_interval_days` 是共享字段，UI 上两方改动需保证一致性。Streamlit 没有实时推送，对方需要刷新页面才能看到——这是已知 alpha 限制，不必为此引入 websocket
- 频率字段虽然只在双方都开启时可见，但底层持久化字段始终存在，避免「开关-字段一致性」死锁
- 不要在「我们」占位区调任何 metrics / query —— 留给 task-11；本任务的占位区只是文案 + 条件分支

## 必读契约

- `docs/api/frontend_streamlit.md`（现有 tab 结构与 components 约定）
- `docs/api/app_reports.md`（task-7 落地的 Report 模型与 repository）
- `docs/api/domain_models.md`（task-7 新增字段）
- `docs/notes/weekly_report.md` §5.1 / §7（服务开关与 UI 状态分支）

## 文档同步

- `docs/api/app_reports.md`：补 metrics / query / policies 三个子章节
- `docs/api/frontend_streamlit.md`：「设置」section 描述、「我们」占位区描述
- `docs/api/infra_ai.md`：`get_report_history` 从「raise NotImplementedError」改为薄包装委托描述
