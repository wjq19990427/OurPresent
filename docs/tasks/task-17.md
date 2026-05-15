# Task 17: 统一 `get_report_history` 与 UI 对 `failed` 报告的语义

**类型**：refactor（接口一致性）
**Branch**：`codex/task-17`
**前置任务**：无
**根因诊断与修复方向**：见 `docs/AUDIT.md` § B4

## 现象

`backend/infrastructure/ai/agent_skills.py` 的 `get_report_history` 返回结果**包含** `failed` 状态报告；而 `frontend/streamlit_app/components.py` 的 `render_report_history` 又过滤掉 `failed`。两套语义并存：agent_skills 作为未来 RAG / 智能体入口被设计为"含 failed 便于排障"，UI 入口则是"过滤 failed 以保体验"。一旦未来智能体直接消费 `get_report_history`，failed 报告内容会污染 LLM 上下文。

## 目标行为

- `get_report_history` 新增显式参数控制是否包含 `failed`，默认与 UI 默认值对齐（不含 failed）
- 排障 / 调试场景下可通过显式参数打开
- 现有调用点行为可能改变（这是本任务的目的），需相应调整调用方使整体语义一致

## 改动范围

**许动**：
- `backend/infrastructure/ai/agent_skills.py`
- 该函数现有的所有调用点
- `backend/tests/` 相关测试

**不许动**：
- `Report` 模型 / `reports_repo` 底层查询接口（`list_reports` 等）
- UI 渲染层 `render_report_history` 自身的过滤逻辑（除非与新参数语义产生冲突，否则不动）

## 验收行为

- `get_report_history(couple_id)` 默认结果不含 `failed`
- 显式传入开关参数后可拿到含 `failed` 的完整历史
- 所有调用方按新默认语义工作，UI 表现与改动前一致
- 单测覆盖默认 / 开关两种调用形态

## 必读契约

- `docs/api/infra_ai.md`（agent_skills 一节）

修改了 `get_report_history` 公开签名，必须同步更新 `docs/api/infra_ai.md`。
