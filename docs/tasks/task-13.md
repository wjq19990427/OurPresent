# Task 13: 收紧 footprint 统计的隐私边界

**类型**：bugfix（防御纵深）
**Branch**：`codex/task-13`
**前置任务**：无
**根因诊断与修复方向**：见 `docs/AUDIT.md` § A2

## 现象

`backend/application/reports/metrics.py:compute_footprint` 对 `shared_at` 为空的 session 默认放行。当前生产路径上不会触发（上游已过滤），但缺少强校验，等于把隐私边界寄托在跨模块的口头约定上。

## 目标行为

footprint 统计的输入契约升级为「shared_at 必填」：

- 一旦传入的 session 缺失 `shared_at`，必须以异常形式中断，而不是静默纳入统计
- 异常类型自选合适的标准异常（`ValueError` / 自定义），但语义需明确指向「契约违反」
- 上游 `get_shared_sessions_for_rag` 的正常输出不应触发该异常（即不破坏现有 happy path）

## 改动范围

**许动**：
- `backend/application/reports/metrics.py`
- `backend/tests/` 下与 reports / metrics 相关的测试文件

**不许动**：
- `get_shared_sessions_for_rag` 的过滤逻辑（A2 是给 metrics 加保险栓，不是改上游）
- `Session` 模型字段定义

## 验收行为

- 给 `compute_footprint` 喂一个 `shared_at=None` 的 session，会抛异常（新增测试覆盖）
- 现有所有 reports 相关测试保持全绿
- 真实流程（`generate_weekly_report` 端到端）行为不变

## 必读契约

- `docs/api/app_reports.md`（metrics / compute_footprint 当前签名与隐私约束章节）

如修改了 `compute_footprint` 公开签名或异常语义，同步更新 `docs/api/app_reports.md`。
