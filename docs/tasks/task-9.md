# Task 9: 情感周报 · DeepSeek 接入与生成 Pipeline

**类型**：feature（核心 AI 接入）
**Branch**：`codex/task-9`
**前置任务**：task-7 / task-8 已合并

## 背景

task-7 / task-8 已把不依赖 LLM 的部分跑通。本任务接入 DeepSeek V4 Flash，完成情感周报生成的完整 pipeline：sampling → metrics → semantic → compose → guard → store。

同时引入**临时手动触发按钮**用于测试。cron 自动触发在 task-10 才接入。

## 目标

1. 新增 `infrastructure/ai/llm_client.py`：DeepSeek 客户端，封装情绪标签 / 共鸣短语 / 天气陈述三类调用
2. 新增 `application/reports/semantic.py`：基于 llm_client 抽取 weather 与 resonance
3. 新增 `application/reports/generate.py`：完整 pipeline 实现 `generate_weekly_report(couple_id, window_end)`
4. 在「🏠 我们」tab 顶部新增**临时手动触发按钮**「🧪 立即生成周报（测试）」
5. 真实渲染最新报告四模块（footprint / weather / resonance / suspense），覆盖 task-8 留下的「开发中」占位

## 改动范围

**许动**：

- `backend/infrastructure/ai/llm_client.py`（新增）
- `backend/infrastructure/ai/agent_skills.py`：`get_shared_sessions_for_rag` 增加 `window=(start, end)` 可选参数
- `backend/application/reports/`：新增 `semantic.py` / `generate.py` / `guard.py`
- `backend/application/reports/errors.py`（新增）：`ReportGenerationError`
- `frontend/streamlit_app/pages/tab_us.py`：替换 task-8 占位区为真实渲染 + 临时手动按钮
- `frontend/streamlit_app/components.py`：若需要新 helper（如渲染 weather / resonance 区块）可加
- `backend/tests/`：补 generate 全链路（mock LLM）、guard 边界、agent_skills window 过滤的测试
- `docs/api/app_reports.md` / `docs/api/infra_ai.md` / `docs/api/frontend_streamlit.md`
- 项目根 `pyproject.toml` / `uv.lock`：按需引入 DeepSeek 客户端依赖
- `.env.example`（新增或更新）：写出 `DEEPSEEK_API_KEY=` 占位（值留空）

**不许动**：

- `backend/application/reports/metrics.py` / `query.py` / `policies.py`（task-8 已定型）
- `backend/application/maintenance/ticking.py`（task-10 才动 cron）
- `backend/domain/models/*`
- `tab_settings.py`（task-8 已完成服务开关；本任务不动）
- `docs/STATUS.md` / `CHANGELOG.md`

## 接口约定

### `llm_client.py`

公开签名（命名可微调，语义不可变）：

```python
def extract_emotions(corpus: list[str]) -> list[EmotionTag]
def extract_resonance(items: list[ResonanceCandidate]) -> list[ResonanceItem]
def compose_weather_narrative(tags: list[EmotionTag]) -> str
```

- 三个函数封装 DeepSeek 调用，统一负责：API key 读取、请求构造、超时、错误捕获、结构化输出解析
- API key 通过环境变量 **`DEEPSEEK_API_KEY`** 读取（已写入项目根 `.env`，gitignored）；`.env.example` 写出变量名占位，不写真实 key
- 失败时抛 `LLMClientError`（在 `llm_client.py` 内部定义），上层 generate 据此判 status=failed
- `EmotionTag` / `ResonanceCandidate` / `ResonanceItem` 是 dataclass 或 TypedDict，结构对齐设计稿 §3 字段（label/weight/phase；day/topic/excerpt）

### `agent_skills.py` 扩展

```python
def get_shared_sessions_for_rag(
    couple_id: str,
    window: tuple[datetime, datetime] | None = None,
) -> list[dict]
```

- 不传 window 时行为与现状一致（占位接口不破坏既有调用方）
- 传 window 时按 `shared_at ∈ [window_start, window_end]` 过滤
- 仍然只返回 `visibility == "shared"`

### `semantic.py`

```python
def extract_semantic(sessions: list[SessionRecord]) -> tuple[dict, list[dict]]
```

- 内部：选字段 → 调 `llm_client` 三个函数 → 拼装 weather / resonance schema → 返回
- 严格遵守设计稿 §6 LLM 输入字段白名单：description / feeling / content_time / user_id；**不传 session_id / 文件路径 / couple_id**
- 失败时抛 `LLMClientError`，由 generate 兜底

### `guard.py`

```python
def check_no_verbatim_quote(report_payload: dict, source_sessions: list[SessionRecord]) -> bool
```

- 实现设计稿 §6 的反原文引用兜底校验
- 拼接 source 的 `description + feeling` 为语料 S
- 对 weather.narrative 与所有 resonance.*.excerpt 做最长公共子串检测，阈值 ≥ 12 字符
- 返回 True 表示通过；False 表示触发兜底
- 阈值常量在文件顶部定义，便于后续调整

### `generate.py`

```python
def generate_weekly_report(
    couple_id: str,
    window_end: datetime | None = None,
) -> Report
```

- `window_end` 默认取 now；window 起点根据 `Couple.weekly_report_interval_days` 倒推
- 流程：
  1. 检查 `service_active_for_couple`，未启用直接抛 `ReportGenerationError`
  2. `get_shared_sessions_for_rag(couple_id, window)` 取数据
  3. 若 `< 3` 条：构造 `status=sparse` 的 Report（仅 footprint + suspense），写库返回
  4. 否则：调 `compute_footprint` / `compute_suspense` / `extract_semantic` → compose → `check_no_verbatim_quote`
  5. guard 通过：`status=ready`，写库返回
  6. guard 不通过 / LLM 失败：`status=failed`，写库返回（不抛异常，让 UI 与 cron 都能拿到结果）
- `model_version` 字段填入实际调用的 DeepSeek 模型名

### 临时手动触发按钮

- 位置：「🏠 我们」tab 顶部，task-8 的占位区内
- 文案：「🧪 立即生成周报（测试）」+ 一行小字「（临时入口，cron 稳定后将由架构师删除）」
- 显示条件：`service_active_for_couple == True`
- 点击行为：调用 `generate_weekly_report(couple_id)`，生成完成后刷新页面展示
- 不做频率冷却、不做二次确认
- **代码注释**：函数与 UI 调用点都要写一行 `# TASK-9 临时按钮，cron 稳定后另开任务删除`，便于将来 grep 定位

### 真实报告渲染（替换 task-8 占位）

- 双方都开启 + 有报告：渲染最新 `status in {"ready", "sparse"}` 报告
- 渲染顺序：footprint → weather → resonance → suspense
- 视觉表达（柱状 / 色块 / 词云 / 卡片堆叠）由实现工自决
- suspense 模块**只展示元数据**（kind 图标 + 剩余天数 + unlock 时间），**不展示** session 任何文本字段
- `status == "failed"` 报告 → UI 不出现，但 `list_reports` 包含

## 验收行为（用户视角）

`uv run streamlit run main.py`：

- 准备：两用户绑定，双方都开启服务，制造至少 3 条 shared 记录
- 点临时手动按钮 → 几秒后页面刷新，「我们」顶部出现一份带四模块的周报
- 该周报的 weather.narrative 不超过 80 字、resonance.excerpt 不超过 8 字符
- 用人工抽检验证：narrative 与 excerpt 不包含 source session 原文中超过 12 字符的连续片段
- 单方关闭服务 → 临时按钮消失，已生成报告仍可看
- 制造 < 3 条 shared 的场景，点按钮 → 生成 sparse 报告，UI 只显示 footprint + 温和提示
- 故意把 API key 改错 → 生成失败，UI 不显示新报告，旧报告仍在；日志中能看到 LLMClientError
- 隐私验证：制造一条 private session，点按钮生成报告后，该 session 内容**不**出现在任何模块（手工对照）

自动化检查：

- `uv run pytest`：新增覆盖
  - sampling window 过滤正确性
  - generate 全链路（mock llm_client）：3 条以下 → sparse；≥ 3 条 → ready；LLM raise → failed；guard 不通过 → failed
  - guard 单测：< 12 字符不触发；≥ 12 字符触发
  - semantic 不传 session_id / 文件路径 / couple_id 给 llm_client（用 spy / mock 验证）
- `uv run ruff check .` 无错

## 已知陷阱

- DeepSeek 兼容 OpenAI 协议，但具体 base_url、模型名、JSON 输出参数有差异；实现工选定 SDK 后注意验证「强制 JSON 输出」是否稳定可靠，必要时在 llm_client 层做一层解析容错
- `extract_semantic` 调三次 LLM 还是一次性调一次（合并 prompt）由实现工决定；但**每次报告生成总 token / 总耗时**需要在 PR 描述里给一个粗略估计，便于后续评估成本
- guard 的 12 字符阈值是「中文 12 个字 ≈ 一句话」的经验值。实测如果误伤过多（短共鸣短语被截断）可以下调到 8；调整后在 `guard.py` 顶部更新常量与注释
- 临时按钮删除时机：等 task-10 cron 自动触发跑稳后，由架构师另开 task；实现工**不要**自作主张把按钮做成正式入口
- sparse 报告也要写 `source_session_ids`，便于排障

## 必读契约

- `docs/api/app_reports.md`（task-7/8 落地的 Report 与 metrics / query / policies）
- `docs/api/infra_ai.md`（agent_skills 现有签名）
- `docs/api/frontend_streamlit.md`（「我们」tab 当前结构）
- `docs/notes/weekly_report.md` §2 / §3 / §6 / §7（Pipeline 阶段、Report schema、隐私约束、UI 接入点）

## 文档同步

- `docs/api/app_reports.md`：补 generate / semantic / guard / errors 章节
- `docs/api/infra_ai.md`：补 `llm_client.py` 整章；`get_shared_sessions_for_rag` 签名更新
- `docs/api/frontend_streamlit.md`：「我们」tab 占位区改为真实渲染描述 + 临时按钮说明（强调将被删除）
- `.env.example`：新增 `DEEPSEEK_API_KEY=` 占位；README 顶部补一行「需 `.env` 中配置 `DEEPSEEK_API_KEY`」（详见 CLAUDE.md §6 README 维护边界）
