# 项目状态快照

**最后更新**：2026-05-10  ·  **当前版本**：v2.2.0  ·  **阶段**：Alpha（本地 Demo） · 收尾技术债

## 一句话项目摘要

OurPresent 是面向情侣的本地 Streamlit 私密记录空间，核心机制是「延时共享」（90 天时间锁）和「冻结期销毁」分手协议。

## 当前架构形态

- 入口：`main.py`（Streamlit 全栈）
- 分层：`frontend/streamlit_app` → `backend/application` → `backend/infrastructure` + `backend/domain` + `backend/config`
- 持久化：SQLite（`data/database.db`），自动迁移旧 `db.json`
- 文件存储：`Assets/Pending/` 与 `Assets/Final/`
- 测试：`backend/tests/`，覆盖 auth / couples / sessions / maintenance

## 最近完成（按时间倒序）

- **task-1：session 子域 dataclass 化**：`application/sessions/*` 与 `frontend/streamlit_app/*` 公开签名 `dict` → `SessionRecord`；dict↔dataclass 转换严格收敛在 `sessions_repo` 持久化边界。已 Review，待合并
- **本地阶段技术债盘点**：4 项技术债按「本地必做 / 部署再做」二分，开了 task-1 / task-2
- **文档体系整合**：`ARCHITECTURE.md` L1 索引、清理死链、补 `STATUS.md` / 实化 `CLAUDE.md` / `AGENTS.md`
- **v2.2.0**：底层从 JSON 切到 SQLite，保留 `load_db()/save_db()` 接口
- **v2.1.0**：application 拆分（auth/couples/sessions/maintenance）+ `domain/models` dataclass + `infrastructure/database` repository

## 下一步（待决策 / 待启动）

1. **task-1 合并**：`codex/task-1` 已 Approve，等用户 merge 到 master
2. **task-2 待启动**：`docs/tasks/task-2.md` — 密码哈希切换到 bcrypt
3. **deferred 到部署阶段**：`tick()` 独立调度器、`load_db()/save_db()` 行级并发改造
4. **Phase 2 预留**：AI 智能体 + RAG。`backend/infrastructure/ai/agent_skills.py` 仅占位

## 已知技术债 / 约束

- `tick()` 仍依赖页面加载触发，无独立调度器（部署期处理）
- 密码哈希为 SHA-256 + 固定盐（task-2 待执行）
- `load_db()/save_db()` 是整库读写，不适合多实例并发（部署期处理）

## 协作约定提醒

- 改 `backend/{application,infrastructure,domain,config}` 或 `frontend/streamlit_app` 任意文件前必读对应 `docs/api/*.md`，改动公开签名/语义后同步更新该 L2 文档
- 任务卡（`docs/tasks/task-N.md`）只写 What 不写 How；Bug 只写症状由实现工自行诊断
- 本文件 ≤ 50 行，任务完成后由架构师维护「最近完成」「下一步」
