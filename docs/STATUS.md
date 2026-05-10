# 项目状态快照

**最后更新**：2026-05-10  ·  **当前版本**：v2.2.0  ·  **阶段**：Alpha（本地 Demo）

## 一句话项目摘要

OurPresent 是面向情侣的本地 Streamlit 私密记录空间，核心机制是「延时共享」（90 天时间锁）和「冻结期销毁」分手协议。

## 当前架构形态

- 入口：`main.py`（Streamlit 全栈）
- 分层：`frontend/streamlit_app` → `backend/application` → `backend/infrastructure` + `backend/domain` + `backend/config`
- 持久化：SQLite（`data/database.db`），自动迁移旧 `db.json`
- 文件存储：`Assets/Pending/` 与 `Assets/Final/`
- 测试：`backend/tests/`，覆盖 auth / couples / sessions / maintenance

## 最近完成（按时间倒序）

- **文档体系整合（本次）**：`technical-report.md` 改造为 `ARCHITECTURE.md` L1 索引、删除重复的 `docs/README.md`、清理所有死链、补 `STATUS.md`、写实 `CLAUDE.md` / `AGENTS.md` 占位符
- **v2.2.0**：底层从 JSON 切到 SQLite，保留 `load_db()/save_db()` 接口
- **v2.1.0**：application 按业务能力拆分（auth/couples/sessions/maintenance），引入 `domain/models` dataclass + `infrastructure/database` repository
- **L2 契约文档拆分**：原 `api-contracts.md` 拆为 `docs/api/{layer}.md` 共 11 份

## 下一步（待决策 / 待启动）

1. **未提交工作入库**：`CLAUDE.md` / `AGENTS.md` / `docs/api/` / `docs/ARCHITECTURE.md` / `docs/STATUS.md` 等改动尚未提交；`text.txt` 是个人讨论笔记，建议加入 `.gitignore` 而非提交。
2. **Beta 阶段方向**：PRD 规划为前后端分离 + 强密码方案（bcrypt/argon2）+ 并发安全 + 独立调度器（替代页面触发的 `tick()`）。需架构师在启动前评估优先级与拆解任务卡。
3. **Phase 2 预留**：AI 智能体（情感周报 + 实时助手）、RAG 接入。`backend/infrastructure/ai/agent_skills.py` 仅占位。

## 已知技术债 / 约束

- `tick()` 仍依赖页面加载触发，无独立调度器
- 密码哈希为 SHA-256 + 固定盐，仅适合本地 Demo
- session UI 层仍部分以 dict 渲染（v2.1.0 重构未一步到位）
- `load_db()/save_db()` 是整库读写，不适合多实例并发

## 协作约定提醒

- 改 `backend/{application,infrastructure,domain,config}` 或 `frontend/streamlit_app` 任意文件前必读对应 `docs/api/*.md`，改动公开签名/语义后同步更新该 L2 文档
- 任务卡（`docs/tasks/task-N.md`）只写 What 不写 How；Bug 只写症状由实现工自行诊断
- 本文件 ≤ 50 行，任务完成后由架构师维护「最近完成」「下一步」
