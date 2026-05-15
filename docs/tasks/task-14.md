# Task 14: 修复周报 resonance 左右对位错乱

**类型**：bugfix（产品体验）
**Branch**：`codex/task-14`
**前置任务**：无
**根因诊断与修复方向**：见 `docs/AUDIT.md` § A3

## 现象

周报 `resonance` 板块的 `user_a_excerpt` / `user_b_excerpt` 由 `sorted(by_user.keys())` 字典序决定归属，与 `Couple.user_a` / `Couple.user_b` 的语义无关。结果：「我们」tab 渲染时，用户可能看到自己说的话出现在伴侣那一列。

## 目标行为（用户可见）

- 任一用户打开自己的周报，resonance 中标注「自己」与「伴侣」的位置始终与 `Couple` 模型对位一致，不随 user_id 字典序漂移
- 同一份 report 在 user_a 和 user_b 两侧渲染时，左右两段引文表达的"谁说的"语义稳定

## 改动范围

**许动**：
- `backend/application/reports/semantic.py`（resonance 候选构造）
- `backend/application/reports/generate.py`（如需向 semantic 传 couple 上下文）
- `frontend/streamlit_app/`（渲染层若需配合调整作者标签）
- `backend/tests/` 下相关测试

**不许动**：
- `Report` / `Couple` 数据库 schema
- LLM prompt 中现有的字段白名单语义（user_id 仍可传入）

## 验收行为

- 构造一对 user_id 字典序与 `couple.user_a` / `couple.user_b` 顺序相反的 couple，跑一次 `generate_weekly_report`：渲染后「自己/伴侣」对位正确
- 现有 reports / semantic 相关测试保持全绿
- 新增覆盖该错位场景的单元测试

## 必读契约

- `docs/api/app_reports.md`（semantic / Report 字段语义）
- `docs/api/frontend_streamlit.md`（「我们」tab 周报渲染部分）

如修改了 `ResonanceCandidate` / `Report.resonance` 字段语义，或 `_resonance_candidates` 的公开签名，同步更新 `docs/api/app_reports.md`。
