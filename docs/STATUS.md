# 项目状态快照

**最后更新**：2026-05-11  ·  **当前版本**：**v3.0.0**  ·  **阶段**：Alpha 本地 Demo · Phase 2 情感周报 v1 已发布

## 一句话项目摘要

OurPresent 是面向情侣的本地 Streamlit 私密记录空间，核心机制是「延时共享」时间锁（可自选、可中途调整、可立即解锁）与「冻结期销毁」分手协议；v3.0.0 起新增基于 DeepSeek 的「情感周报」AI 模块，NVC 四模块温和陈述，隐私三层约束。

## 当前架构形态

- 入口：`main.py`（Streamlit 全栈）
- 分层：`frontend/streamlit_app` → `backend/application` → `backend/infrastructure` + `backend/domain` + `backend/config`
- 持久化：SQLite（`data/database.db`），单一来源
- 文件存储：`Assets/Pending/` 与 `Assets/Final/`
- AI：DeepSeek V4 Flash（`.env: DEEPSEEK_API_KEY`），仅周报模块使用
- 测试：`backend/tests/`，覆盖 auth / couples / sessions / maintenance / reports，整库测试 71+

## 最近完成（按时间倒序）

- **v3.0.0 发布**：Phase 2 情感周报 v1 完整落地；Opus 复审技术债清单入库（`docs/phase2_audit.md`）；README / PRD / state-machines / user-guide / extension-guide / ARCHITECTURE 全面同步
- **task-11：UI 收尾**：报告渲染迁到 `components.py`；「我们」9 行状态矩阵；历史入口在「设置」；frozen 开关只读
- **task-10：cron 自动触发**：`scheduling.py` 纯函数；`tick()` 扩展遍历 couples；失败重试进程级 set 追踪
- **task-9：DeepSeek 接入与 pipeline**：`llm_client` / `semantic`（字段白名单）/ `guard`（LCS 阈值 12）/ `generate`（sparse / ready / LLM fail / guard fail 四路径）
- **task-7/8：数据底座 + metrics + 服务开关 UI**：`Report` + `reports` 表 + repo；`User.weekly_report_enabled` / `Couple.weekly_report_interval_days`；`destroy_couple_data` 联动
- **Phase 2 设计与任务卡入库**：`docs/weekly_report.md` + 5 张任务卡
- **task-6：UI 三栏化 + 共享双向可见**：5 tab → 3 tab，「我们」改 `couple_id + visibility==shared` 过滤
- **task-4/5：时间锁灵活化**：`unlock_at` 用户自选 + pending_unlock 流动性（追加 / 改时 / 立即解锁 / 撤回）
- **早期里程碑**：v2.2.0 SQLite 迁移 · v2.1.0 分层重构 · 文档体系整合 · task-1~3 数据层收尾

## 下一步（待决策 / 待启动）

1. **Phase 2 周报技术债**（按优先级清理 `docs/phase2_audit.md` 中 13 项；A 级 4 项数据/隐私相关）
2. **另开 task 删除临时手动按钮**：`tab_us.py` 两处 `# TASK-9 临时按钮` 为定位标记，cron 验证稳定后清除
3. **收敛 `app_reports.md` 重复内容**：Report 模型 / reports_repo 同时存在于三份 L2，下次触碰 application 层时顺手清理
4. **deferred 到部署阶段**：`tick()` 独立调度器、`load_db()/save_db()` 行级并发改造、累积 `_migrate_db` 清算
5. **Phase 2 其他 AI 模块**：NVC 润色器 / 安全着陆舱 / 专属两人词典（`docs/AI.md` 第二章）

## 已知技术债 / 约束

- 详见 `docs/phase2_audit.md`（Phase 2 周报 13 项）
- `tick()` 依赖页面加载触发，无独立调度器（部署期处理）
- `load_db()/save_db()` 整库读写，不适合多实例并发（部署期处理）

## 协作约定提醒

- 改 `backend/{application,infrastructure,domain,config}` 或 `frontend/streamlit_app` 前必读对应 `docs/api/*.md`，改动公开签名/语义后同步更新该 L2
- 任务卡只写 What 不写 How；Bug 只写症状由实现工自行诊断
- 本文件 ≤ 50 行，任务完成后由架构师维护
