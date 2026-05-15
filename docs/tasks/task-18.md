# Task 18: 防止 `user_id` 经 LLM 复述泄露到 narrative

**类型**：bugfix（隐私边界 + guard 增强）
**Branch**：`codex/task-18`
**前置任务**：无
**根因诊断与修复方向**：见 `docs/AUDIT.md` § B5

## 现象

`backend/application/reports/semantic.py:_corpus_item` 把真实 `user_id`（如 `usr_a1b2c3d4`）作为白名单字段传给 LLM。`user_id` 本身不是 PII，但 LLM 有概率把它复述到 `narrative` / `topic` 字段。当前 guard 只比对 narrative 与 `description + feeling` 的最长公共子串，不扫描 user_id，乌龙文本会直接展示给用户。

## 目标行为

- guard 阶段对 LLM 输出做 `user_id` 黑名单扫描：若 narrative / topic / 其他用户可见字段中出现任何参与本次报告生成的真实 user_id，则按现有失败语义处理（标记 failed / 触发已有的失败路径）
- 扫描覆盖范围以「用户在 UI 上能直接看到的 LLM 生成字段」为准
- 不破坏 happy path：正常生成的报告不会因为这个黑名单被误判失败

## 改动范围

**许动**：
- `backend/application/reports/guard.py`
- 必要时 `backend/application/reports/generate.py`（仅为把 user_id 列表传给 guard）
- `backend/tests/` 中 guard / reports 相关测试

**不许动**：
- `semantic.py` 的 `_corpus_item` 字段白名单（本卡选短期黑名单方案，不做长期的 user_1/user_2 映射重构）
- LLM 调用 prompt 模板

## 验收行为

- 构造一个含 user_id 的 mock LLM 输出，guard 判定为失败
- 正常 LLM 输出（不含 user_id）guard 通过
- 现有 reports / guard 测试全绿
- 新增针对 user_id 泄露的测试用例

## 必读契约

- `docs/api/app_reports.md`（guard / failure 章节）

新增 guard 规则属于行为变化，需在 `docs/api/app_reports.md` 中 guard 一节明确「user_id 黑名单」这一失败路径。
