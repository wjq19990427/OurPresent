# Task 15: 校验 `DEEPSEEK_BASE_URL` 的 scheme

**类型**：bugfix（防御纵深）
**Branch**：`codex/task-15`
**前置任务**：无
**根因诊断与修复方向**：见 `docs/AUDIT.md` § A4

## 现象

`backend/infrastructure/ai/llm_client.py` 读取 `DEEPSEEK_BASE_URL` 后未做 scheme 校验。若环境变量被误设为 `http://...` 或 `file://...` 等非 https scheme，`urllib.request.urlopen` 会照常执行——明文请求会泄露 Authorization 头里的 API key，本地 scheme 还可能读取本地文件。

## 目标行为

- LLM 客户端在启动 / 首次调用时校验 base URL 必须是 `https://` scheme
- 校验失败需以明确的客户端异常中断（沿用现有 `LLMClientError` 或同层级异常），且错误信息指向"非法 base URL"，不暴露完整环境变量内容
- 默认值（`https://api.deepseek.com`）保持可用，不破坏现有调用

## 改动范围

**许动**：
- `backend/infrastructure/ai/llm_client.py`
- `backend/tests/` 下 llm_client 相关测试

**不许动**：
- 任何 application 层调用 LLM 的代码（异常类型如沿用现有的，调用方无感）
- `.env` / 部署文档（运维相关变更不在本卡范围）

## 验收行为

- 把 `DEEPSEEK_BASE_URL` 设为 `http://example.com`，构造 LLM 客户端时即抛异常
- 设为 `file:///etc/passwd` 同样抛异常
- 未设置或设为合法 https URL，行为与改动前一致
- 新增对应单元测试

## 必读契约

- `docs/api/infra_ai.md`（若存在；否则按现有 `docs/api/` 索引确认 llm_client 归属的 L2 文档）

如修改了 `LLMClient` 公开构造签名或新增异常类型，同步更新对应 L2 文档。
