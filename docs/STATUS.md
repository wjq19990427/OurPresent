# 项目状态快照

**最后更新**：2026-05-11  ·  **当前版本**：v2.3.0  ·  **阶段**：Alpha（本地 Demo） · 时间锁灵活化（task-4 + task-5）feature-complete

## 一句话项目摘要

OurPresent 是面向情侣的本地 Streamlit 私密记录空间，核心机制是「延时共享」时间锁（可自选、可中途调整、可立即解锁）和「冻结期销毁」分手协议。

## 当前架构形态

- 入口：`main.py`（Streamlit 全栈）
- 分层：`frontend/streamlit_app` → `backend/application` → `backend/infrastructure` + `backend/domain` + `backend/config`
- 持久化：SQLite（`data/database.db`），单一来源，无旧 JSON 兼容
- 文件存储：`Assets/Pending/` 与 `Assets/Final/`
- 测试：`backend/tests/`，覆盖 auth / couples / sessions / maintenance

## 最近完成（按时间倒序）

- **task-5：pending_unlock 流动性增强**：新增 `unlock_now` / `reschedule_unlock` / `append_to_session` 三个用例；UI 上「修改时间」「立即解锁」需勾选确认；`request_unlock` 立即-分支同步对齐 `unlock_at = shared_at = now`，统一「shared 时 unlock_at 等于实际共享时刻」不变量。已合并
- **task-4：自定义共享开放时间**：`SessionRecord.unlock_at` 字段落地；`request_unlock(session_id, unlock_at)` 必填目标时间；`tick()` 改为基于 `unlock_at` 判定；UI 提供 7 档预设 + 日历 + 「立即」；引入 `_migrate_db` 轻量 ALTER TABLE 模式承载 schema 演进。已合并
- **task-3：删除旧 JSON 库迁移路径**：`db.py` 中 `_load_legacy_json` / `_migrate_legacy_json_if_needed` / `_has_any_data` / 纯 sessions 数组兼容分支全部移除；`LEGACY_DB_PATH` 常量删除；本地 `data/database.db` 与 `Assets/Pending|Final/*` 清空。已合并
- **task-2：密码哈希切换到 bcrypt**：`users_repo._hash_password` / `verify_password` 改用 `bcrypt.hashpw`+`bcrypt.checkpw`，独立盐，单一路径；旧 SHA-256 双盐兼容彻底删除。已合并
- **task-1：session 子域 dataclass 化**：`application/sessions/*` 与 `frontend/streamlit_app/*` 公开签名 `dict` → `SessionRecord`；dict↔dataclass 转换严格收敛在 `sessions_repo` 持久化边界。已合并
- **本地阶段技术债盘点**：4 项技术债按「本地必做 / 部署再做」二分，开了 task-1 / task-2
- **文档体系整合**：`ARCHITECTURE.md` L1 索引、清理死链、补 `STATUS.md` / 实化 `CLAUDE.md` / `AGENTS.md`
- **v2.2.0**：底层从 JSON 切到 SQLite，保留 `load_db()/save_db()` 接口

## 下一步（待决策 / 待启动）

1. **task-6 UI 大改版**（进行中）：5 tab → 3 tab（🏠 我们 / 📝 我的 / ⚙️ 设置）；修复「情侣空间」单向可见 bug（`tab_shared.py:24` 过滤错位）；左右分边 + 状态徽章。任务卡已入库，业务层零改动
2. **deferred 到部署阶段**：`tick()` 独立调度器、`load_db()/save_db()` 行级并发改造、累积 `_migrate_db` 调用清算
3. **Phase 2 预留**：AI 智能体 + RAG。`backend/infrastructure/ai/agent_skills.py` 仅占位

## 已知技术债 / 约束

- `tick()` 仍依赖页面加载触发，无独立调度器（部署期处理）
- `load_db()/save_db()` 是整库读写，不适合多实例并发（部署期处理）
- `_days_until_unlock` 取整逻辑边界不一致：整 N 天显示 N 天，N 天 1 秒显示 N+1 天（task-5 或后续可顺手收敛）

## 协作约定提醒

- 改 `backend/{application,infrastructure,domain,config}` 或 `frontend/streamlit_app` 任意文件前必读对应 `docs/api/*.md`，改动公开签名/语义后同步更新该 L2 文档
- 任务卡（`docs/tasks/task-N.md`）只写 What 不写 How；Bug 只写症状由实现工自行诊断
- 本文件 ≤ 50 行，任务完成后由架构师维护「最近完成」「下一步」
