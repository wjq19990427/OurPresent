# Task 19: 收紧 `_session_day` fallback 的日期格式校验

**类型**：bugfix（cosmetic / 数据卫生）
**Branch**：`codex/task-19`
**前置任务**：无
**根因诊断与修复方向**：见 `docs/AUDIT.md` § B6

## 现象

`backend/application/reports/semantic.py:_session_day` 与 `backend/application/reports/metrics.py:_session_day` 在主路径失败时 fallback 到 `content_time[:10]`。`content_time` 是用户自由输入字段，可能是「2026 年春节」、「上周二」、`"abc"` 等非日期文本。这些非法切片结果会作为 `by_day` 字典的 key 进入 resonance 配对，最终出现在周报 `resonance.day` 字段中，用户看到「上周二 同日共享」之类的乌龙。

## 目标行为

- `_session_day` 的所有返回路径都必须满足 `YYYY-MM-DD` 格式校验
- 主路径与 fallback 取到的值都不符合该格式时，视为该 session 没有有效日期：不参与 resonance 配对 / 不进入按日聚合统计
- 「不参与」的处理方式以「丢弃 / 跳过」为准，不抛异常打断报告生成

## 改动范围

**许动**：
- `backend/application/reports/semantic.py`
- `backend/application/reports/metrics.py`
- `backend/tests/` 中 reports / semantic / metrics 相关测试

**不许动**：
- `Session.content_time` 字段定义 / 输入端校验（用户自由输入是产品设计，不在本卡范围）

## 验收行为

- 构造 `content_time = "上周二"` 的 session，不会出现在 resonance / 按日聚合结果中
- 构造合法 `YYYY-MM-DD` 或主路径可解析的 session 行为与改动前一致
- 现有 reports 全部测试保持绿色
- 新增针对非法 fallback 的测试

## 必读契约

- `docs/api/app_reports.md`（semantic / metrics 章节中 `_session_day` 行为描述）

`_session_day` 是模块内私有函数，无公开签名变更则无需更新 L2。但「非法日期被丢弃」属于隐含语义变化，若 `docs/api/app_reports.md` 中描述了按日聚合行为，需要同步澄清这一过滤规则。
