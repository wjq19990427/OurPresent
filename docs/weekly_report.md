# 情感周报 · 工程设计稿

**状态**：决策完成，已拆 task-7 ~ task-11，等真实 shared 数据后施工
**最后更新**：2026-05-11
**对应 PRD**：FR-20 / FR-21（第二阶段 · 智能体模块 A）
**产品定调来源**：[`docs/AI.md`](./AI.md) 第一章
**LLM 厂商**：DeepSeek V4 Flash（用户提供 API）

> 本文只回答「要什么 / 边界在哪 / 模块如何切」。具体 prompt 措辞、视觉表达、SDK 选择留给实现工，见 §9。

## 1. 设计立场

四个模块按 NVC 框架切分：

1. **关系足迹**（NVC「观察」）：客观计数与时间分布，不评价
2. **情绪气象站**（NVC「感受」）：情绪倾向抽取，天气式陈述呈现
3. **同频与共鸣瞬间**：同日同主题 / 同情绪交叠的正向强化
4. **未尽的悬念**：联动 pending_unlock 倒计时的温柔提示

**主动不做**（产品边界，写死在 system prompt 与 schema 里）：

- 不揣测「需要」与「请求」
- 不评判任何一方行为
- 不引用对方原文（共鸣模块的关键短语 ≤ 8 字符例外，且仅限 shared 内容）
- 不读 `private` / `pending_unlock` 内容

## 2. Pipeline 与模块拆分

```text
trigger (cron / 手动)
    ↓
sampling   ── 取 couple 当周 shared sessions
    ↓
metrics    ── 纯 Python：计数、kind 分布、活跃日、评论数
    ↓
semantic   ── 调 LLM：情绪标签、共鸣短语、weather narrative
    ↓
compose    ── 拼装四模块 JSON
    ↓
guard      ── 反原文引用兜底校验
    ↓
store      ── 写入 reports 表
    ↓
render     ── 「我们」tab 顶部展示
```

各阶段放在哪：

| 阶段 | 位置 | 备注 |
|------|------|------|
| trigger | `backend/application/maintenance/ticking.py` 扩展 | 复用 `tick()` 调度入口 |
| sampling | `backend/infrastructure/ai/agent_skills.py:get_shared_sessions_for_rag` | 增加 `window=(start, end)` 参数 |
| metrics | `backend/application/reports/metrics.py`（新增） | 纯 Python，可单测 |
| semantic | `backend/application/reports/semantic.py`（新增） | 走 `infrastructure/ai/llm_client.py`（新增） |
| compose / guard / store | `backend/application/reports/generate.py`（新增） | 用例入口 |
| query | `backend/application/reports/query.py`（新增） | 列表与详情 |
| render | `frontend/streamlit_app/pages/tab_us.py` 顶部 expander | 不开新 tab |

## 3. 数据模型 · `Report`

新增 dataclass `Report`（`backend/domain/models/report.py`）：

```jsonc
{
  "report_id":     "rpt_20260510_cp_12345678",   // YYYYMMDD_<couple_id>
  "couple_id":     "cp_12345678",
  "window_start":  "2026-05-04 00:00:00",        // 含，本地时区
  "window_end":    "2026-05-10 23:59:59",        // 含
  "generated_at":  "2026-05-11 03:00:00",
  "model_version": "claude-haiku-4-5-20251001",  // 实现工选定后写入
  "footprint":     { ... },                      // 模块 1
  "weather":       { ... },                      // 模块 2
  "resonance":     [ ... ],                      // 模块 3
  "suspense":      [ ... ],                      // 模块 4
  "status":        "ready",                      // ready / failed / sparse
  "source_session_ids": ["...", "..."]           // 审计用，UI 不展示
}
```

落库：

- 新表 `reports`，由 `_migrate_db()` 创建
- `load_db()` 顶层字典扩展键 `reports`（沿用整库 dict 编程模型不变量）
- 字段类型由实现工在 repository 层确定（JSON blob vs 拆列），优先选择 JSON blob 减小迁移面

各模块 JSON 形态（schema 终态由实现工最终敲定）：

- **footprint** — 纯结构化，metrics 阶段产出：
  ```jsonc
  {
    "total": 7,
    "by_kind": { "photo": 3, "video": 1, "text": 3 },
    "active_days": 4,
    "comment_count": 12,
    "by_author": { "usr_aaa": 4, "usr_bbb": 3 }
  }
  ```
- **weather** — semantic 阶段产出：
  ```jsonc
  {
    "tags": [
      { "label": "焦虑", "weight": 0.3, "phase": "early" },
      { "label": "放松", "weight": 0.5, "phase": "late" }
    ],
    "narrative": "≤ 80 字，天气式陈述，不点名"
  }
  ```
- **resonance** — semantic 阶段产出：
  ```jsonc
  [
    {
      "day":             "2026-05-06",
      "topic":           "想吃火锅",
      "user_a_excerpt":  "≤ 8 字短语",
      "user_b_excerpt":  "≤ 8 字短语"
    }
  ]
  ```
- **suspense** — metrics 阶段产出，纯元数据，不抽取内容：
  ```jsonc
  [
    {
      "session_id":     "20260601_120000",
      "unlock_at":      "2026-06-10 12:00:00",
      "days_remaining": 30,
      "kind":           "photo"
    }
  ]
  ```

## 4. 接口契约（L2 草案）

新增 L2 文档 `docs/api/app_reports.md`（实现期与代码同步落地）。本节是占位骨架。

公开签名（最小集）：

```python
# backend/application/reports/generate.py
def generate_weekly_report(couple_id: str, window_end: datetime | None = None) -> Report
    """当前 couple 的本周（或指定结束周）报告。已存在则返回已存在的；不存在则生成。"""

def regenerate_report(report_id: str) -> Report
    """失败重试，覆盖原 report 内容。"""

# backend/application/reports/query.py
def list_reports(couple_id: str) -> list[Report]
def get_report(report_id: str) -> Report | None

# backend/infrastructure/ai/llm_client.py（新增模块）
def extract_emotions(texts: list[str]) -> list[EmotionTag]
def extract_resonance(pairs: list[tuple[str, str]]) -> list[ResonanceItem]
def compose_narrative(tags: list[EmotionTag]) -> str
```

`backend/infrastructure/ai/agent_skills.py` 原 `get_report_history` 占位 → 改为薄包装 → 委托给 `application/reports/query.list_reports`。

## 5. 服务开关、触发与频率

### 5.1 服务开关（双方协议制）

- **开关粒度**：个人意愿，存在 `User.weekly_report_enabled`（默认 False）
- **生效条件**：couple 双方**都**开启时服务才生效
- **单方开启态 UI**：开启者侧显示「⌛ 等待对方一同开启」+ 邀请文案；未开启者侧显示「对方已开启周报，要不要一起？」
- **关闭副作用**：任一方关闭 → 立刻停止后续生成；**历史报告保留**（与 session 同生命周期，dissolve 时一并销毁）

### 5.2 触发节律

- **间隔**：`Couple.weekly_report_interval_days`，默认 7；用户在「设置」可选 7 / 14 / 30
  - 间隔是 couple 共享配置，任一方修改立即对双方生效（与「这是你俩共同的空间」语义一致）
  - 间隔字段仅在双方都开启服务后可见可改
- **触发时刻**：上次生成时间 + 间隔 ≤ now 时由 `tick()` 触发；首次触发以「双方都开启的时刻」为锚点
- **窗口**：上一次报告 `window_end` 到本次触发时刻；若是首次报告，窗口取 `now - interval_days` 到 `now`

### 5.3 临时手动触发（测试用，将来删除）

- 「🏠 我们」tab 顶部增加「🧪 立即生成周报（测试）」按钮
- 不受频率 / 上次生成时间约束，点一次生成一次
- 仅在双方都开启服务时显示
- 任务卡 task-9 引入此按钮；cron 自动触发稳定后由架构师另开 task 删除
- 实现工在该按钮的 UI 文案与代码注释中**显式标注「临时」**，便于后续定位删除

### 5.4 数据不足兜底

- 本窗口 shared 记录 < 3 条 → 写一条 `status=sparse` 的报告，仅含 footprint，不调 LLM
- sparse 报告**入库**，UI 正常展示（不做「累计 N 周隐藏」之类的自动屏蔽——用户偏好显式控制，不要替用户做决定）

### 5.5 失败处理

- LLM 调用失败 → `status=failed`，next tick 重试一次，再失败放弃
- UI 不展示 failed 报告，但 `list_reports` 包含（便于排障）

## 6. 隐私与 NVC 约束（硬约束）

**数据访问层**：

- 唯一数据入口 `get_shared_sessions_for_rag(couple_id, window)`
- 任何 `private` / `pending_unlock` 数据不得进入 pipeline 任意阶段
- 跨 couple 隔离由 `couple_id` 在应用层强制

**LLM 输入约束**：

- 传入字段限定：`description / feeling / content_time / user_id`
- 不传 `session_id`（防 LLM 写回引用）
- 不传 `files` 路径（防文件名泄露）
- 不传 `couple_id`（防交叉污染）

**LLM 输出约束**：

- 强制结构化输出（function calling / response_format JSON schema）
- `resonance.*.excerpt` 长度上限 8 字符，超长由 compose 阶段截断或丢弃
- `weather.narrative` 上限 80 字符

**反原文引用兜底校验**（compose 后、store 前）：

- 把当周 source sessions 的 `description + feeling` 拼成语料 `S`
- 对 `weather.narrative` 与所有 `resonance.*.excerpt` 与 `S` 做最长公共子串检测
- 单一连续子串 ≥ 12 字符 → 整份 report 标 `status=failed`，写日志，next tick 重试一次

**System Prompt 要点**（实现工写 prompt 时的硬性条款）：

- 禁止对双方行为做对错判断
- 输出仅围绕「观察 / 感受」，不写「需要 / 请求」
- 不写「你们应该 / 建议」类祈使句
- 不点名具体一方（用「这一周的开头」「周中」之类的时间锚，不用「A 表达了…」）

## 7. UI 接入点

### 7.1 「🏠 我们」tab

- 顶部 `📊 周报` expander，默认收起；服务关闭态不显示 expander，避免占位
- 双方都开启 + 有 ready 报告 → 展示最新报告，渲染顺序 footprint → weather → resonance → suspense
- 双方都开启 + 还没生成过 → 显示「邀请你写下第一周的共享记录」
- 任一方未开启 → 见 §5.1 单方开启态文案
- sparse 报告 → 正常展示 footprint，加一句温和陈述「这周共享记录较少，留些空白也好」
- failed 报告 → UI 不出现卡片
- 临时手动触发按钮 → 见 §5.3

### 7.2 「⚙️ 设置」tab

新增「情感周报服务」section：

- 我的开关（绑定 `User.weekly_report_enabled`，可独立切换）
- 对方开启状态展示：「✅ 对方已开启」/「⌛ 对方尚未开启」
- 频率选择（仅双方都开启后可见可改）：7 / 14 / 30 天
- 历史入口：「查看周报历史 →」，浅模态展示 `list_reports` 倒序

### 7.3 视觉细节

- 天气图 / 情绪色块 / 词云的具体选型由实现工自决，不在本设计范围

## 8. 与现有用例联动

- **`destroy_couple_data()`**（`application/couples/uncoupling.py` 调用链）：销毁 couple 时一并删除 `reports` 表中 `couple_id` 命中的全部行。需在该用例追加一条；改后同步 `docs/api/app_couple.md` 与 `docs/api/app_sessions.md`（destruction 子域）。
- **冻结期**：`couple_status=frozen` 时 trigger 跳过该 couple，不生成新报告；历史报告可读、可导出。
- **冻结期导出**：`export_couple_data()` 输出 ZIP 中包含 `reports.json`（该 couple 全部历史周报）。

## 9. 留给实现工自决（How）

- DeepSeek 接入细节：SDK（`openai` 兼容客户端配 base_url / 裸 `httpx` / 官方 SDK）、密钥读取（环境变量名）、超时与重试参数
- prompt 模板、few-shot、温度参数
- 情绪标签策略：自由抽取 vs 固定枚举（推荐固定枚举，便于 weather 可视化稳定）
- `reports` 表的列设计：JSON blob 单列 vs 多列拆分
- `_migrate_db` 增加 `reports` 表与 `users` / `couples` 新字段的 SQL
- cron 颗粒度：在 `tick()` 里按「上次生成时间 + 间隔」判断
- 「天气图 / 色块 / 词云」的 Streamlit 实现
- semantic 阶段的并发与缓存：单次报告一次性调用 vs 流式

## 10. 决策记录（已闭环）

| # | 问题 | 决策 |
|---|------|------|
| Q1 | LLM 厂商 | **DeepSeek V4 Flash**（用户有现成 API） |
| Q2 | 数据不足阈值 | 默认 **< 3 条** 进入 sparse |
| Q3 | 报告频率 | 默认 **7 天**，双方都开启后可在设置中调整（7 / 14 / 30） |
| Q4 | 手动触发对方需否确认 | **否**。两人同视图，任一方都能触发 |
| Q5 | 历史周报生命周期 | **与 session 同生命周期**，dissolve 时一并销毁 |
| Q6 | sparse 报告是否入库 | **入库**，UI 正常展示 footprint；不做「累计 N 周隐藏」的自动屏蔽 |
| Q7 | 服务开关粒度 | **个人意愿**，双方都开启才生效；单方开启显示等待对方文案 |
| Q8 | 临时手动触发按钮 | task-9 引入 + 显式标注「临时」，cron 跑稳后另开 task 删除 |

## 11. 实施分阶段（已拆任务卡）

| 任务 | 内容 | 是否依赖 LLM | 文件 |
|------|------|--------------|------|
| task-7 | `Report` dataclass + `reports` 表 + `User`/`Couple` 新字段 + repository CRUD + destruction 联动 | 否 | [`tasks/task-7.md`](./tasks/task-7.md) |
| task-8 | metrics 纯 Python 计算 + 「设置」服务开关 UI + 双方启用判定 | 否 | [`tasks/task-8.md`](./tasks/task-8.md) |
| task-9 | DeepSeek 客户端 + semantic 抽取 + guard 校验 + `generate_weekly_report` 用例 + 临时手动触发按钮 | 是 | [`tasks/task-9.md`](./tasks/task-9.md) |
| task-10 | cron 触发 + 失败重试 + sparse 兜底 + 冻结期跳过 | 是 | [`tasks/task-10.md`](./tasks/task-10.md) |
| task-11 | 「我们」周报渲染 + 历史列表 + 频率自定义 UI + 全部状态文案 | 否 | [`tasks/task-11.md`](./tasks/task-11.md) |

task-7 / task-8 不依赖 LLM，可立即开工；task-9 起需要 DeepSeek API 与少量真实 shared 数据。临时手动按钮的删除将由架构师在 task-10 稳定后另开任务（暂不预拆）。

## 12. 与 AI.md 第二章「轻量辅助工具」的分工

本设计**只覆盖**情感周报。`docs/AI.md` 第二章列出的另外三个模块属于独立的 AI 子项目，各自另开设计稿：

- NVC 润色器（输入辅助）
- 安全着陆舱（解锁时刻的破冰建议）
- 专属两人词典（高频黑话提取）

这些模块的数据流、触发机制、隐私边界都与周报不同（尤其 NVC 润色器要触达 private 输入，权限模型完全不同），不应塞进同一份设计。
