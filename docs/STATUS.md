# 项目状态快照

**最后更新**：2026-05-13  ·  **当前版本**：**v3.0.0**（Unreleased 含 A2~A4 / B3~B6 技术债清理 + UI 一致性收尾）  ·  **阶段**：Alpha 本地 Demo · **战略转向商业化 + E2EE**（详见 `docs/product-direction.md`）· 云端方向 task 全部冻结待 E2EE 决策

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

- **task-20c 合并（codex 实现）**：合成生成端切到「一份 persona = 一对情侣 = 一份剧本」；persona 拆为 `lin_xia_together.json` / `mo_qin_destroyed.json`，`build_script(persona, timeline, outcome, outcome_reason, weeks)` 单一入口，结局由 LLM 输出 outcome/outcome_reason 写入 frontmatter，离线 fallback 读 persona `expected_outcome`，CLI 增 `--outcome` 覆盖；`destroyed` 剧本前段保留正常延时共享 + 互动，结尾才进冷淡 → uncouple → `destroy_couple_data`；旧"任务20_*.md"产物按角色重命名，`build_destroy_script` 入口移除
- **task-20b 后续修复（用户监督 codex）**：session `created_at` 对齐 event 日期（02c6b6e）→ 销毁样例语义/时间修正（be04208）→ 主剧本与销毁剧本拆为两份 md（b38f0e0），`run_synth.py` 一次生成两份产物、`actions.py` 抽出 `build_destroy_script` 独立骨架
- **task-20b 合并（codex 实现）**：合成剧本载体从 JSON 改为 Markdown 单源 —— 自研 540 行 stdlib YAML 解析器（不引新依赖）、frontmatter 装结构 + 正文按时间序铺事件/记录/actions、`script_io.validate_script` 在写库前断言事件引用与时间精度；新增 `template.md` 手写模板（可直接 replay）、9 项 pytest 覆盖 round-trip / 三类损坏剧本 / 模板可重放 / 编辑落库；IO seam 收敛在 `cli.py`，`actions.py / run_synth.py` 零改
- **task-21 任务卡入库**：PG 迁移 + Docker Compose，只换介质保留整库 dict 语义，application/domain/frontend 零感知；task-20 剧本作为跨 DB 一致性验收基线；同步顺手清理 task-20 四条遗留
- **task-20 合并（codex 实现）**：`tools/synth/` 落地 MiniMax-M2.5 合成流水（角色卡 / 时间线 / 延时表达行为），contextmanager 隔离 monkey-patch，`SYNTH_DB_PATH` 硬约束 + Assets 隔离，必经 application 层（含 `add_comment` 互动 / `start_uncouple` + `destroy_couple_data`），自带 3 项 pytest（分布 / 二次回放等价 / 生产路径拒绝）
- **B 级技术债清理（task-16/17/18/19）**：B3 `_load_dotenv_api_key` walk-up 找 `pyproject.toml` / B4 `get_report_history` 增 `include_failed` 显式开关 / B5 guard 增 `blocked_user_ids` 黑名单扫描扩展可见字段 / B6 `_session_day` 严格 `YYYY-MM-DD` 校验
- **A 级技术债清理（task-13/14/15）**：`compute_footprint` 输入契约收紧（缺失 shared_at 抛异常）/ resonance 严格按 `Couple.user_a/b` 对位 / `DEEPSEEK_BASE_URL` 启动期 https scheme 校验
- **task-12a/12b：UI 一致性收尾**：替换 Streamlit `use_container_width` 废弃参数；登录页改造为单列移动端风格
- **v3.0.0 发布**：Phase 2 情感周报 v1 完整落地；Opus 复审技术债清单入库（`docs/phase2_audit.md`）；文档全量同步
- **task-9~11**：DeepSeek pipeline · cron 自动触发 · UI 收尾（报告渲染 / 状态矩阵 / 历史入口）
- **task-7/8**：`Report` 模型 + reports 表 + repo · 服务开关 UI · `destroy_couple_data` 联动
- **Phase 2 设计入库**：`docs/weekly_report.md` + 5 张任务卡
- **task-6**：5 tab → 3 tab；「我们」改 `couple_id + visibility==shared` 双向可见
- **task-4/5**：时间锁灵活化（`unlock_at` 自选 + pending_unlock 流动性）
- **早期里程碑**：v2.2.0 SQLite · v2.1.0 分层重构 · task-1~3 数据层

## 下一步（待决策 / 待启动）

> **战略转向 2026-05-13**：项目商业化路径锁定（微信小程序 + 云端），卖点回归延时表达本身，AI 暂缓到上市后。隐私底线提到端到端加密，详见 `docs/product-direction.md`。

1. **task-23 待开工**：微信小程序作为 E2EE 客户端的可行性调研（纯事实报告，输出 `docs/research/wechat-miniprogram-crypto.md`）。任务卡 `docs/tasks/task-23.md`。这份报告是配对协议 + 设备恢复 UX 设计的事实基础
2. **配对协议 + 备份策略架构决策卡**（task-23 完成后立项）：Tier 1 + Tier 2 退路 + Tier 3 兜底框架已锁（详见 `docs/product-direction.md`），剩余需基于 task-23 的事实边界设计协议
2. **task-21 冷藏**：原任务卡前提（整库明文 load_db/save_db 不变）与 E2EE 后"服务端只持有密文 + 元数据"形态不兼容；E2EE 架构决策敲定后重写
3. **task-20/20b/20c 合成数据流水冻结扩展**：商业化路径下 P0 (demo seed) 失效、P1 (AI 回归语料) 推后；现有产物保留作为未来后端回放基线，但不再追加 LLM 联动 / 新结局
4. **Phase 2 周报相关全部推后**：AI 模块整体暂缓，`docs/phase2_audit.md` 的剩余技术债待 AI 重启时再评
5. **另开 task 删除临时手动按钮**：`tab_us.py` 两处 `# TASK-9 临时按钮`，cron 验证稳定后清除（小修补，不阻塞战略）
6. **task-22 FastAPI 包装暂缓**：要等 E2EE 决策确定服务端形态后再谈

## 已知技术债 / 约束

- 详见 `docs/phase2_audit.md`（Phase 2 周报 13 项）
- `tick()` 依赖页面加载触发，无独立调度器（部署期处理）
- `load_db()/save_db()` 整库读写，不适合多实例并发（部署期处理）

## 协作约定提醒

- 改 `backend/{application,infrastructure,domain,config}` 或 `frontend/streamlit_app` 前必读对应 `docs/api/*.md`，改动公开签名/语义后同步更新该 L2
- 任务卡只写 What 不写 How；Bug 只写症状由实现工自行诊断
- 本文件 ≤ 50 行，任务完成后由架构师维护
