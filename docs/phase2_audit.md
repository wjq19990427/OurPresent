# Phase 2 情感周报 · Opus 复审审计

**审计时间**：2026-05-11
**审计范围**：task-7 ~ task-11（Phase 2 第一版完整落地）
**审计模型**：Opus 4.7（此前 review 由 Sonnet 完成）
**结论**：功能完整可发布 v3.0.0；以下列出可发布门槛之下但需要纳入技术债账本的 13 项

> 本文档不阻断发版，是 Opus 视角的二次复审记录，留给未来迭代时按优先级清理。每条注明 **影响等级 / 修复成本 / 修复建议**。

---

## A. 高优 · 影响数据一致性或隐私边界

### A1. `tick()` 内嵌 `generate_weekly_report` 触发了非原子的 load/save 嵌套

**位置**：`backend/application/maintenance/ticking.py:100` + `backend/application/reports/generate.py:_persist`

**现象**：
- `tick()` 在自己持有的 in-memory `db` 上推进 session / couple / token 状态
- 然后调用 `generate_weekly_report` → `_persist` → `create_report/update_report` → 这两个 repo 函数**各自独立调用 `load_db()` 和 `save_db()`**
- 中途的 `save_db` 会把 tick 主流程**尚未 flush 的 session 状态变更覆盖丢失**（因为 repo 加载到的是磁盘旧状态，不知道 tick 已经把某个 session 改成 shared）

**实际影响**：
- 单一 Streamlit 进程下，并发风险存在但触发概率低（用户加载页面 → tick → 持续几百 ms 完成）
- 若同一窗口内：tick 把 session A 推进 pending_unlock→shared，紧接着生成报告。报告 `save_db` 会用旧的 sessions 状态覆盖，导致 A 又退回 pending_unlock
- 下一次 tick 会重新推进，最终一致——但中间状态会被外部观察到，且 `shared_at` 时间戳被刷写两次

**修复建议**：
- 短期：`_persist` 不再走 `load_db/save_db` 整库路径，改成直接对 SQLite `reports` 表的单表 INSERT/UPDATE（绕过整库 dict 模型）
- 长期：在「下一步」已列的 `load_db()/save_db()` 重构里一并处理

**影响等级**：🔴 高（数据正确性，但触发条件窄）
**修复成本**：中（绕过整库 dict 需要 reports_repo 与 db.py 协同改）

---

### A2. `compute_footprint` 对缺失 `shared_at` 的 session 默认放行

**位置**：`backend/application/reports/metrics.py:51-59`

**现象**：
```python
if (not session.shared_at)
or (window_start <= shared_at <= window_end)
```

「shared_at 为空就放行」这个分支在生产路径上是 dead code（输入已由 `get_shared_sessions_for_rag` 预过滤），但若上游过滤逻辑出现回退，会让 `private` / `pending_unlock` session 静默进入 footprint 统计。

**实际影响**：
- 当前无回退路径，但隐私边界靠**两个独立模块的约定**维系，缺乏强校验
- 出问题不会抛异常，只是产出错误数字

**修复建议**：要求 `session.shared_at` 必填，缺失即抛 `ValueError` 而非静默放行——把契约从"约定"变成"断言"

**影响等级**：🟡 中（隐私边界保险栓）
**修复成本**：低（3 行改动 + 1 个测试）

---

### A3. `resonance.user_a_excerpt` / `user_b_excerpt` 与 couple 模型的 `user_a` / `user_b` 不对应

**位置**：`backend/application/reports/semantic.py:_resonance_candidates`

**现象**：
```python
user_ids = sorted(by_user)
first_user, second_user = user_ids[0], user_ids[1]
first_text = " ".join(...)  # 赋给 user_a_text
```

`first/second_user` 来自 `sorted(by_user.keys())` 的字母序，与 `Couple.user_a` / `Couple.user_b` 的实际语义无关。

**实际影响**：
- 「我们」tab 渲染 resonance 用 `left, right = st.columns(2)`，左列 `user_a_excerpt`，右列 `user_b_excerpt`
- 这两个 excerpt 哪个属于"自己"哪个属于"伴侣"取决于双方 user_id 字典序，与 UI 设定的「自己靠右、伴侣靠左」语义脱钩
- 用户可能看到自己说的话出现在伴侣那一列——**轻度认知错位**

**修复建议**：
- `_resonance_candidates` 接收 `couple: Couple` 参数，按 `couple.user_a` / `couple.user_b` 对齐
- 或：UI 渲染时用 `report` 自带的 `user_a_excerpt` 字段名作为 fallback，渲染附作者标签明确"谁说的"

**影响等级**：🟡 中（产品体验，非数据正确性）
**修复成本**：低（约 10 行）

---

### A4. `DEEPSEEK_BASE_URL` 环境变量未做 scheme 校验

**位置**：`backend/infrastructure/ai/llm_client.py:14`

**现象**：
```python
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
```

若环境变量被误设为 `http://...` 或 `file:///etc/passwd` 等 scheme，`urllib.request.urlopen` 会照常执行，发出明文请求或读取本地文件。

**实际影响**：
- 默认值是 https，正常使用无风险
- 但运维误操作 / 被攻击者污染 env 时缺少最后一道防线
- 报告输入虽然只有脱敏字段，但 API key 会随 Authorization 头泄露给非预期接收方

**修复建议**：客户端启动时校验 `DEEPSEEK_BASE_URL.startswith("https://")`，否则抛 `LLMClientError`

**影响等级**：🟡 中（防御纵深）
**修复成本**：低（2 行）

---

## B. 中优 · 影响产品体验或可演进性

### B1. 手动测试按钮会重置 cron 节律

**位置**：`frontend/streamlit_app/pages/tab_us.py` 临时按钮 → `generate_weekly_report` → 产出新 report 的 `window_end = now`

**现象**：
- `should_generate_for_couple` 用 `previous_window_end + interval <= now` 判定
- 手动生成后，`previous_window_end = now`，cron 自动触发要等下一个完整 interval 才会发生
- 用户感知上：「我手动生成一次，自动周报就晚了一周」

**实际影响**：
- task-9 临时按钮即将删除（task TBD），届时问题自然消失
- 当前仅影响内测期；用户若依赖手动按钮做 demo，可能误以为 cron 失灵

**修复建议**：
- 短期（按钮删除前）：在 STATUS / user-guide 注明手动按钮会推迟下次自动生成
- 长期：手动 vs cron 用独立的"上次时间"字段区分，但工程成本高，不建议为临时按钮做

**影响等级**：🟡 中（仅内测期相关）
**修复成本**：极低（文档化）/ 高（独立字段）

---

### B2. `guard.VERBATIM_QUOTE_THRESHOLD = 12` 阈值是经验值，未经真实语料验证

**位置**：`backend/application/reports/guard.py:7`

**现象**：
- 12 字符 LCS 用于检测 LLM 是否原文复述
- 中英文混排 / 表情符号 / 通用短语（如「今天天气真好」）的边界未实测

**实际影响**：
- 阈值过低 → 大量 ready 报告被误判 failed，UI 看不到内容
- 阈值过高 → 真正的原文复述漏过

**修复建议**：
- 部署后收集 ~20 份真实报告样本（包含 ready 与 failed），人工标注是否真的"原文复述"
- 根据 PR/RP 调整阈值（10/14/16 都可能更合理）
- 当前 12 仅作为"宁错杀不放过"的起点

**影响等级**：🟡 中（产品质量，可观测）
**修复成本**：极低（改一个常量 + 重跑）

---

### B3. `_load_dotenv_api_key` 用 `parents[3]` 定位项目根，路径耦合脆弱

**位置**：`backend/infrastructure/ai/llm_client.py:46`

**现象**：
- 如果 `llm_client.py` 被移到别处（如挪出 `backend/infrastructure/ai/`），`parents[3]` 不再指向项目根
- 没有 fallback / 校验

**修复建议**：
- 改用「向上找 `pyproject.toml`」的 walk-up 方式
- 或引入 `python-dotenv` 库（增加一个依赖，但消除自己写解析的负担）

**影响等级**：🟢 低（仅在重构时被发现）
**修复成本**：低

---

### B4. `get_report_history` 与 UI `render_report_history` 对 `failed` 的处理不一致

**位置**：
- `backend/infrastructure/ai/agent_skills.py:get_report_history` 返回**包含** `failed`
- `frontend/streamlit_app/components.py:render_report_history` 过滤掉 `failed`

**现象**：
- `agent_skills` 作为未来 RAG / 智能体的统一入口，"包含 failed"是为排障预留
- UI 入口"过滤 failed"是为体验
- 两套语义并存，未来若智能体直接消费 `get_report_history`，可能把 failed 信息呈现给 LLM 进一步污染输出

**修复建议**：
- `get_report_history(couple_id, include_failed: bool = False)` 显式参数化
- 默认 False 与 UI 对齐；调试需要时显式开

**影响等级**：🟢 低（当前 UI 直接走 `list_reports` 不经此入口）
**修复成本**：极低

---

### B5. `_corpus_item` 把 `user_id` 传给 LLM

**位置**：`backend/application/reports/semantic.py:_corpus_item`

**现象**：
- 任务卡明确允许 user_id 进入 LLM 字段白名单
- user_id 是不透明短串（`usr_a1b2c3d4`），不构成 PII
- 但 LLM 可能把它当作"作者标记"复述到 narrative 或 topic 里

**实际影响**：
- guard 不检查 narrative 是否包含 user_id（只检查与 description+feeling 的最长公共子串）
- 一旦泄露，用户看到的就是「usr_a1b2c3d4 提到了…」这种乌龙

**修复建议**：
- 短期：guard 增加 user_id 黑名单串扫描
- 长期：semantic 层用临时映射（`user_1` / `user_2`）替换真实 user_id，输出后再翻译回来

**影响等级**：🟢 低（DeepSeek 实测如果出现这种行为再改也不迟）
**修复成本**：低（黑名单 5 行）/ 中（映射方案 30 行）

---

### B6. `_session_day` fallback 到 `content_time[:10]` 可能产生非日期字符串

**位置**：`backend/application/reports/semantic.py:_session_day` 与 `metrics.py:_session_day`

**现象**：
- `content_time` 是用户自由输入的「事件/内容发生时间」字段
- 用户可能输入「2026 年春节」、「上周二」、「`abc`」
- 切片 `[:10]` 后变成「2026 年春节」、「上周二」、`"abc"` 等非日期字符串
- 这些字符串会作为 `by_day` 字典的 key，参与 resonance 配对
- 最终出现在 `resonance.day` 字段里，UI 直接展示

**实际影响**：用户看到周报里写「上周二 同日共享」——略尴尬，但不破坏功能

**修复建议**：fallback 也要校验是否符合 `YYYY-MM-DD` 格式，否则丢弃该 session 不参与 resonance

**影响等级**：🟢 低（cosmetic）
**修复成本**：极低

---

### B7. `_persist` 的 `get_report` + `create_report` / `update_report` 非原子

**位置**：`backend/application/reports/generate.py:_persist`

**现象**：
- 三步操作之间没有事务保护
- 同一 couple 同一日的两次并发 `generate_weekly_report`（如手动 + cron），可能两个都看到「不存在」→ 两次 `create_report` → 主键冲突或重复行

**实际影响**：alpha 单进程下罕见，但当前测试未覆盖

**修复建议**：与 A1 一并处理，下沉到 `reports_repo` 用 `INSERT ... ON CONFLICT(report_id) DO UPDATE` 单语句原子

**影响等级**：🟢 低（与 A1 同根因）
**修复成本**：随 A1

---

## C. 低优 · 待数据 / 待清理

### C1. `_resonance_candidates` 的 `topic="同日共享"` 是占位

**位置**：`backend/application/reports/semantic.py:51`

**现象**：传给 LLM 的 `topic` 固定字符串，LLM 在 prompt 中没有被告知如何从候选文本提炼真正的 topic

**修复建议**：
- 改进 prompt 让 LLM 主动从 `user_a_text` / `user_b_text` 概括 topic
- 或废弃 `ResonanceCandidate.topic` 字段

**影响等级**：🟢 低
**修复成本**：低（调 prompt）

---

### C2. 手动按钮不 catch `ReportGenerationError` / 其他异常

**位置**：`frontend/streamlit_app/pages/tab_us.py` 手动按钮分支

**现象**：
- 用户点击按钮时，若服务状态变为非 active（例如对方刚关闭开关 + 页面未刷新），`generate_weekly_report` 会抛 `ReportGenerationError`
- Streamlit 直接展示红色 traceback

**修复建议**：临时按钮即将删除，无需修复

**影响等级**：🟢 低
**修复成本**：极低 / 无需

---

### C3. 失败重试状态进程级、重启即清空

已在 `docs/api/app_reports.md` 和 STATUS 标注为已知 alpha trade-off。部署期处理 `tick()` 独立调度器时一并解决。

---

## D. 文档漂移（v3.0.0 同步时一并修复）

| 文档 | 漂移点 | 修复方向 |
|------|--------|----------|
| `README.md` | "AI 能力第二阶段预留，当前未正式接入"；当前能力列表缺周报 | 改为已接入；新增「情感周报」能力项 |
| `docs/PRD.md` | §4 阶段表 Phase 2 仍标"规划中"；§3.2 仍说"满 90 天"；FR-20/21 描述未对齐落地版本 | Phase 2 改"周报已完成"；删除"90 天"硬编码；FR 描述补落地范围 |
| `docs/state-machines.md` | `tick()` 解锁条件仍写 `upload_time ≥ 90 天`（task-4 起改 `unlock_at`） · 导出规则说"不含 AI 生成报告"但未注明是设计缺口 | 改 `unlock_at`；导出说明改为"暂不含周报，后续补齐" |
| `docs/user-guide.md` | 整体停留在 task-6 前的 5 tab 结构与术语，全文未提周报 | 改写为 3 tab + 周报小节 |
| `docs/extension-guide.md` | 周报相关章节仍以"预留接口"语气，未反映已落地 | 标注已落地，并指向 `weekly_report.md` |
| `docs/ARCHITECTURE.md` | §4 关键不变量未列「情感周报隐私三层约束」 | 补一条 |
| `docs/ARCHITECTURE.md` | L2 表中 `app_reports.md` 覆盖代码描述仅含 model + repo，未含 application 全套 | 改为 "Report 模型 + 仓储 + metrics / query / policies / semantic / guard / generate / scheduling" |

---

## 不在本审计范围

- 现有 task-1～6 的代码（已发布 v2.x 系列经过多次 review）
- 部署期才处理的整库 dict 模型债（STATUS 已列）
- 未来 Phase 2 其他 AI 模块（NVC 润色器等）

---

*本文档与代码同步维护。技术债清理后请在对应章节标注 [✅ 已修复 · vX.Y.Z] 或删除该条。*
