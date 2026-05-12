# Task 16: `_load_dotenv_api_key` 解除项目根硬编码路径耦合

**类型**：refactor（健壮性）
**Branch**：`codex/task-16`
**前置任务**：无
**根因诊断与修复方向**：见 `docs/phase2_audit.md` § B3

## 现象

`backend/infrastructure/ai/llm_client.py` 中 `_load_dotenv_api_key` 用 `Path(__file__).parents[3]` 硬定位项目根读取 `.env`。一旦 `llm_client.py` 被挪出 `backend/infrastructure/ai/`（重构 / 重新分层），`parents[3]` 不再指向项目根，环境变量读取静默失败，没有 fallback 也没有错误提示。

## 目标行为

- 项目根定位策略改为「特征文件向上 walk-up」：从当前文件起逐级向上找包含项目识别标志（如 `pyproject.toml`）的目录
- walk-up 到文件系统根仍未找到时，行为需明确（直接 fallback 到「跳过 .env 读取」即可，与当前找不到 `.env` 的语义一致）
- `.env` 解析逻辑保持不变（只改定位方式）

## 改动范围

**许动**：
- `backend/infrastructure/ai/llm_client.py`
- `backend/tests/` 相关测试

**不许动**：
- 不引入 `python-dotenv` 第三方依赖（保持零依赖解析）
- `.env` 文件格式 / 字段约定

## 验收行为

- `llm_client.py` 即使被搬动层级，仍能正确定位到项目根的 `.env`
- 项目根不存在 `.env` 时静默跳过（与现状一致）
- 已有 llm_client 测试保持绿色

## 必读契约

- `docs/api/infra_ai.md`

`_load_dotenv_api_key` 是模块内私有函数，无公开签名变更则无需更新 L2。若调整了 LLM 客户端的公开行为，同步更新 `docs/api/infra_ai.md`。
