# 项目状态快照

**最后更新**：2026-05-11  ·  **当前版本**：v2.4.0  ·  **阶段**：Alpha（本地 Demo） · Phase 2 task-11 已合并，情感周报功能完整可用

## 一句话项目摘要

OurPresent 是面向情侣的本地 Streamlit 私密记录空间，核心机制是「延时共享」时间锁（可自选、可中途调整、可立即解锁）和「冻结期销毁」分手协议。

## 当前架构形态

- 入口：`main.py`（Streamlit 全栈）
- 分层：`frontend/streamlit_app` → `backend/application` → `backend/infrastructure` + `backend/domain` + `backend/config`
- 持久化：SQLite（`data/database.db`），单一来源，无旧 JSON 兼容
- 文件存储：`Assets/Pending/` 与 `Assets/Final/`
- 测试：`backend/tests/`，覆盖 auth / couples / sessions / maintenance

## 最近完成（按时间倒序）

- **task-11：UI 收尾**：报告渲染迁到 `components.py`（`render_weekly_report` / `render_report_history`）；「我们」9 行状态矩阵完整覆盖；历史入口落在「设置」（active / frozen 均可见）；频率文案 `7 天 / 每周`；frozen 开关只读；隐私说明一句话；临时手动按钮保留。已合并 · **情感周报功能阶段性完整**
- **task-10：cron 自动触发**：`scheduling.py` 纯函数（couple_status / 双方开关 / 间隔 / 重试 / 首次锚点 `created_at`）；`tick()` 扩展遍历 couples，单 couple 异常不阻断其他；失败重试进程级 set 追踪（`failed → retry → skip`）；冻结期跳过；11 种状态参数化测试。已合并
- **task-9：DeepSeek 接入与生成 pipeline**：`llm_client.py`（裸 urllib + 手写 .env 解析，无额外依赖）+ `semantic.py`（LLM 输入字段白名单） + `guard.py`（LCS 反原文校验，阈值 12 字符）+ `generate.py`（sparse / ready / LLM fail / guard fail 四路径）+ 临时手动按钮 + 四模块真实渲染；隐私测试覆盖「session_id / couple_id / 文件路径不进 LLM」。已合并
- **task-7/8：数据底座 + metrics + 服务开关 UI**：`Report` dataclass + `reports` 表 + `reports_repo`；`User.weekly_report_enabled` / `Couple.weekly_report_interval_days`；`destroy_couple_data` 联动；metrics / query / policies；「设置」服务 section。已合并
- **Phase 2 情感周报设计与任务卡入库**：`docs/weekly_report.md` NVC 四模块 + Pipeline 七阶段 + 隐私三层约束；8 个开放问题闭环，5 张任务卡线性拆分
- **task-6：UI 大改版 + 共享双向可见 bug 修复**：5 tab → 3 tab（🏠 我们 / 📝 我的 / ⚙️ 设置），默认落地「我们」；`tab_us.py` 过滤改为 `couple_id + visibility==shared`，自己 shared 给伴侣的内容双方都能看到；iMessage 风左右分边；新增 `_status_badge`（草稿 / 仅自己 / 倒计时·还有 N 天 / 已分享）；`render_detail.selected_state_key` 改为 keyword-only 必填。业务层零改动。已合并
- **task-5：pending_unlock 流动性增强**：新增 `unlock_now` / `reschedule_unlock` / `append_to_session` 三个用例；UI 上「修改时间」「立即解锁」需勾选确认；`request_unlock` 立即-分支同步对齐 `unlock_at = shared_at = now`，统一「shared 时 unlock_at 等于实际共享时刻」不变量。已合并
- **task-4：自定义共享开放时间**：`SessionRecord.unlock_at` 字段落地；`request_unlock(session_id, unlock_at)` 必填目标时间；`tick()` 改为基于 `unlock_at` 判定；UI 提供 7 档预设 + 日历 + 「立即」；引入 `_migrate_db` 轻量 ALTER TABLE 模式承载 schema 演进。已合并
- **task-3：删除旧 JSON 库迁移路径**：`db.py` 中 `_load_legacy_json` / `_migrate_legacy_json_if_needed` / `_has_any_data` / 纯 sessions 数组兼容分支全部移除；`LEGACY_DB_PATH` 常量删除；本地 `data/database.db` 与 `Assets/Pending|Final/*` 清空。已合并
- **task-2：密码哈希切换到 bcrypt**：`users_repo._hash_password` / `verify_password` 改用 `bcrypt.hashpw`+`bcrypt.checkpw`，独立盐，单一路径；旧 SHA-256 双盐兼容彻底删除。已合并
- **task-1：session 子域 dataclass 化**：`application/sessions/*` 与 `frontend/streamlit_app/*` 公开签名 `dict` → `SessionRecord`；dict↔dataclass 转换严格收敛在 `sessions_repo` 持久化边界。已合并
- **早期里程碑**：v2.2.0 SQLite 迁移 · 文档体系整合 · 技术债盘点 · task-1~3 数据层收尾

## 下一步（待决策 / 待启动）

1. **另开 task 删除临时手动按钮**：`tab_us.py` 两处 `# TASK-9 临时按钮` 为定位标记，cron 验证稳定后清除
2. **收敛 `app_reports.md` 重复内容**：Report 模型 / reports_repo 同时存在于三份 L2，下次触碰 application 层时顺手清理
3. **deferred 到部署阶段**：`tick()` 独立调度器、`load_db()/save_db()` 行级并发改造、累积 `_migrate_db` 清算
4. **Phase 2 其他 AI 模块**：NVC 润色器 / 安全着陆舱 / 专属两人词典（`docs/AI.md` 第二章）

## 已知技术债 / 约束

- `tick()` 仍依赖页面加载触发，无独立调度器（部署期处理）
- `load_db()/save_db()` 是整库读写，不适合多实例并发（部署期处理）
- `_days_until_unlock` 取整逻辑边界不一致：整 N 天显示 N 天，N 天 1 秒显示 N+1 天（task-5 或后续可顺手收敛）

## 协作约定提醒

- 改 `backend/{application,infrastructure,domain,config}` 或 `frontend/streamlit_app` 任意文件前必读对应 `docs/api/*.md`，改动公开签名/语义后同步更新该 L2 文档
- 任务卡（`docs/tasks/task-N.md`）只写 What 不写 How；Bug 只写症状由实现工自行诊断
- 本文件 ≤ 50 行，任务完成后由架构师维护「最近完成」「下一步」
