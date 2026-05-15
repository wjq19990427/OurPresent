# Task 10: 情感周报 · cron 触发与失败重试

**类型**：feature（自动调度）
**Branch**：`codex/task-10`
**前置任务**：task-9 已合并并经过手动按钮验证可生成

## 背景

task-9 已实现完整生成 pipeline，但只能手动触发。本任务把生成逻辑挂到 `tick()` 上，让周报按 `Couple.weekly_report_interval_days` 自动推进。

## 目标

1. 扩展 `tick()`：每 couple 按间隔自动触发 `generate_weekly_report`
2. 失败重试：上一次 failed 的 couple 在 next tick 重试一次，再失败则放弃直到下一周期
3. 冻结期跳过：`couple_status in {"frozen", "dissolved", "pending_bind"}` 时不生成
4. 服务开关前置：双方任一未开启时不生成

## 改动范围

**许动**：

- `backend/application/maintenance/ticking.py`
- `backend/application/reports/scheduling.py`（新增）：触发判定的纯函数
- `backend/tests/`：tick 触发逻辑的测试
- `docs/api/app_maintenance.md` / `docs/api/app_reports.md`

**不许动**：

- `backend/application/reports/generate.py` / `semantic.py` / `guard.py`（task-9 定型）
- `frontend/**`（不动 UI）
- `backend/infrastructure/**`
- `docs/STATUS.md` / `CHANGELOG.md`

## 接口约定

### `scheduling.py`

公开签名：

```python
def should_generate_for_couple(couple: Couple, db: dict, now: datetime) -> bool
def previous_report_window_end(couple_id: str, db: dict) -> datetime | None
```

- `should_generate_for_couple` 综合判定：
  - couple_status 必须是 `active`
  - 双方 `weekly_report_enabled` 都为 True
  - `now >= previous_window_end + interval_days`；首次（previous 为 None）以两人都开启之后的某个锚点为准（实现工选定锚点，但需稳定可复现，写在 L2 文档里）
  - 上次报告 status == failed 且 next tick 标记未消耗 → 允许重试一次
- 两个函数都是纯函数，方便单测

### `tick()` 扩展

- 在现有「session 推进 / 冻结期销毁 / token 清理」之后追加一遍循环：
  - 遍历所有 couple
  - 对每个满足 `should_generate_for_couple` 的 couple 调用 `generate_weekly_report`
  - 不阻塞 tick 主链路：单个 couple 报告生成失败不影响其他 couple
- 失败重试计数策略：实现工自决（存在 Report 自身字段、或独立计数表、或 ticking 内部内存缓存）；语义上「连续两次失败放弃」，下一周期重新开窗
- 全部生成完毕后才 `save_db()`，复用现有整库读写模型

## 验收行为（用户视角）

`uv run streamlit run main.py`：

- 准备：两用户绑定，双方都开启服务，制造 ≥ 3 条 shared 记录
- 把 `Couple.weekly_report_interval_days` 临时改成 1（DB 直接改或 UI 改）
- 等待 / 触发一次页面加载（tick 触发器） → 自动生成一份新报告（无需点临时按钮）
- 把间隔改回 7，立即触发页面加载 → 不会再生成新报告（上次刚生成完）
- 把 API key 改错 → 触发 tick → 生成 failed 报告 → 触发第二次 tick → 重试一次仍 failed → 触发第三次 tick → 跳过，等下一周期
- 一方关闭服务后再触发 tick → 不生成
- 一方发起解绑（couple 进入 frozen） → 触发 tick → 不生成；冻结期历史报告仍可读

自动化检查：

- `uv run pytest`：新增覆盖
  - `should_generate_for_couple` 在 8 种状态组合下结果正确（开关 × couple_status × 上次时间）
  - tick 中单 couple 失败不影响其他 couple
  - failed → retry → failed → 放弃的状态机
- `uv run ruff check .` 无错

## 已知陷阱

- `tick()` 当前只在页面加载时触发，没有独立 scheduler。这是已知 alpha 限制（见 `docs/STATUS.md`），本任务**不要**为周报单独引入 scheduler；接受「无人访问就不生成」的妥协，后续与 `tick()` 独立调度器一并处理（已在 STATUS 下一步标注）
- 重试计数如果落到 Report 本体字段，要在 task-7 之外再加一个字段——和 task-7 边界冲突；推荐放在 ticking 内部内存缓存或独立小表，由实现工选
- 「首次触发锚点」要避免出现「刚开启服务就立刻生成一份空空如也的报告」。实现工读 `Couple` 字段后选定一个合理锚点（如 `created_at` 或开启服务的时刻），并写进 `docs/api/app_reports.md`
- 临时手动按钮在本任务中**不动**；架构师在本任务合并并 cron 验证稳定后另开 task 删除

## 必读契约

- `docs/api/app_maintenance.md`（`tick()` 现有职责）
- `docs/api/app_reports.md`（task-7/8/9 已落地的接口）
- `docs/notes/weekly_report.md` §5（触发与频率）

## 文档同步

- `docs/api/app_maintenance.md`：`tick()` 职责追加「按间隔触发周报生成」
- `docs/api/app_reports.md`：新增 scheduling 章节
