# 项目状态快照

**最后更新**：2026-05-11  ·  **当前版本**：v2.4.0  ·  **阶段**：Alpha（本地 Demo） · Phase 2 task-8 已合并，DeepSeek key 就绪

## 一句话项目摘要

OurPresent 是面向情侣的本地 Streamlit 私密记录空间，核心机制是「延时共享」时间锁（可自选、可中途调整、可立即解锁）和「冻结期销毁」分手协议。

## 当前架构形态

- 入口：`main.py`（Streamlit 全栈）
- 分层：`frontend/streamlit_app` → `backend/application` → `backend/infrastructure` + `backend/domain` + `backend/config`
- 持久化：SQLite（`data/database.db`），单一来源，无旧 JSON 兼容
- 文件存储：`Assets/Pending/` 与 `Assets/Final/`
- 测试：`backend/tests/`，覆盖 auth / couples / sessions / maintenance

## 最近完成（按时间倒序）

- **task-8：metrics + 服务开关 UI**：新增 `application/reports/{metrics,policies,query}.py`；「设置」增「情感周报服务」section（开关 / 对方状态 / 频率）；「我们」增占位区 4 分支；`get_report_history` 改薄包装。已合并
- **task-7：情感周报数据底座**：新增 `Report` dataclass（`slots=True` + 显式 `from_dict`）、`reports` 表（JSON blob 拆 4 列）、`reports_repo` CRUD；`User.weekly_report_enabled` / `Couple.weekly_report_interval_days` 字段落地并经 `_migrate_db` ALTER 路径兼容旧库；`destroy_couple_data_in_db` 联动清理 reports；新增 `test_old_sqlite_schema_migrates_new_report_fields` 覆盖旧 schema 升级路径。已合并
- **Phase 2 情感周报 task-7~11 任务卡入库**：设计 8 个开放问题全部闭环（DeepSeek V4 Flash / 双方协议开关 / couple 级频率 / sparse 入库且不自动隐藏 / 临时手动按钮）；5 张任务卡按「数据底座 → metrics + 服务开关 UI → DeepSeek 接入与生成 → cron 自动触发 → UI 收尾」线性递进；task-7/8 不依赖 LLM 可立即开工
- **Phase 2 情感周报工程设计稿**：`docs/weekly_report.md` 入库。NVC 四模块（足迹/气象/共鸣/悬念）切分、Pipeline 七阶段、`Report` dataclass + `reports` 表、隐私三层约束（数据访问/LLM 输入/输出 + 反原文兜底校验）
- **task-6：UI 大改版 + 共享双向可见 bug 修复**：5 tab → 3 tab（🏠 我们 / 📝 我的 / ⚙️ 设置），默认落地「我们」；`tab_us.py` 过滤改为 `couple_id + visibility==shared`，自己 shared 给伴侣的内容双方都能看到；iMessage 风左右分边；新增 `_status_badge`（草稿 / 仅自己 / 倒计时·还有 N 天 / 已分享）；`render_detail.selected_state_key` 改为 keyword-only 必填。业务层零改动。已合并
- **task-5：pending_unlock 流动性增强**：新增 `unlock_now` / `reschedule_unlock` / `append_to_session` 三个用例；UI 上「修改时间」「立即解锁」需勾选确认；`request_unlock` 立即-分支同步对齐 `unlock_at = shared_at = now`，统一「shared 时 unlock_at 等于实际共享时刻」不变量。已合并
- **task-4：自定义共享开放时间**：`SessionRecord.unlock_at` 字段落地；`request_unlock(session_id, unlock_at)` 必填目标时间；`tick()` 改为基于 `unlock_at` 判定；UI 提供 7 档预设 + 日历 + 「立即」；引入 `_migrate_db` 轻量 ALTER TABLE 模式承载 schema 演进。已合并
- **task-3：删除旧 JSON 库迁移路径**：`db.py` 中 `_load_legacy_json` / `_migrate_legacy_json_if_needed` / `_has_any_data` / 纯 sessions 数组兼容分支全部移除；`LEGACY_DB_PATH` 常量删除；本地 `data/database.db` 与 `Assets/Pending|Final/*` 清空。已合并
- **task-2：密码哈希切换到 bcrypt**：`users_repo._hash_password` / `verify_password` 改用 `bcrypt.hashpw`+`bcrypt.checkpw`，独立盐，单一路径；旧 SHA-256 双盐兼容彻底删除。已合并
- **task-1：session 子域 dataclass 化**：`application/sessions/*` 与 `frontend/streamlit_app/*` 公开签名 `dict` → `SessionRecord`；dict↔dataclass 转换严格收敛在 `sessions_repo` 持久化边界。已合并
- **早期里程碑**：v2.2.0 SQLite 迁移 · 文档体系整合 · 技术债盘点 · task-1~3 数据层收尾

## 下一步（待决策 / 待启动）

1. **task-9 可开工**：DeepSeek API key 已配（`.env:DEEPSEEK_API_KEY`）；需积累 ≥ 3 条真实 shared 数据后启动 semantic / guard / generate pipeline + 临时手动按钮。合并后由架构师把 `app_reports.md` 收敛为只描述 application 层（与 `domain_models.md` / `infra_db.md` 重复内容待清理）
2. **task-9 起需要 DeepSeek API key 与真实 shared 数据**：用户提供 API、积累 ≥ 3 条 shared 后启动
3. **task-10 跑稳后另开 task 删除临时手动按钮**：task-9 引入的「🧪 立即生成周报（测试）」是过渡入口
4. **deferred 到部署阶段**：`tick()` 独立调度器、`load_db()/save_db()` 行级并发改造、累积 `_migrate_db` 调用清算
5. **Phase 2 其他 AI 模块**：NVC 润色器 / 安全着陆舱 / 专属两人词典（`docs/AI.md` 第二章），周报落地后各自另开设计稿

## 已知技术债 / 约束

- `tick()` 仍依赖页面加载触发，无独立调度器（部署期处理）
- `load_db()/save_db()` 是整库读写，不适合多实例并发（部署期处理）
- `_days_until_unlock` 取整逻辑边界不一致：整 N 天显示 N 天，N 天 1 秒显示 N+1 天（task-5 或后续可顺手收敛）

## 协作约定提醒

- 改 `backend/{application,infrastructure,domain,config}` 或 `frontend/streamlit_app` 任意文件前必读对应 `docs/api/*.md`，改动公开签名/语义后同步更新该 L2 文档
- 任务卡（`docs/tasks/task-N.md`）只写 What 不写 How；Bug 只写症状由实现工自行诊断
- 本文件 ≤ 50 行，任务完成后由架构师维护「最近完成」「下一步」
