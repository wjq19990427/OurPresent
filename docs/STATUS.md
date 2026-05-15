# 项目状态快照

**最后更新**：2026-05-15  ·  **当前版本**：**v3.0.0**（Unreleased 含 A2~A4 / B3~B6 技术债清理 + UI 一致性收尾）  ·  **阶段**：Phase 0 · Alpha 本地 Demo · 战略转向商业化 + E2EE（详见 `docs/DIRECTION.md` / `docs/ROADMAP.md`）

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

- **task-23 合并（codex 调研）**：微信小程序作为 E2EE 客户端的事实边界报告落盘 `docs/research/wechat-miniprogram-crypto.md`，覆盖加密 API / `wx.setStorage` 语义 / 安全存储位置 / 钥匙丢失场景 / 包体积 / 性能 / 备份载体 / OOB 配对通道 8 个问题，每条带「结论 / 证据 / 状态有效性 / 分级」；末尾两节硬约束清单将直接驱动下一张配对协议决策卡。研究产出不该上 CHANGELOG，合并前已剔除 codex 添加的 CHANGELOG 条目（任务卡边界规则已补进 `CLAUDE.md`）
- **task-20c 合并（codex 实现）**：合成生成端切到「一份 persona = 一对情侣 = 一份剧本」；persona 拆为 `lin_xia_together.json` / `mo_qin_destroyed.json`，`build_script(persona, timeline, outcome, outcome_reason, weeks)` 单一入口，结局由 LLM 输出 outcome/outcome_reason 写入 frontmatter，离线 fallback 读 persona `expected_outcome`，CLI 增 `--outcome` 覆盖；`destroyed` 剧本前段保留正常延时共享 + 互动，结尾才进冷淡 → uncouple → `destroy_couple_data`；旧"任务20_*.md"产物按角色重命名，`build_destroy_script` 入口移除
- **task-20b 后续修复（用户监督 codex）**：session `created_at` 对齐 event 日期（02c6b6e）→ 销毁样例语义/时间修正（be04208）→ 主剧本与销毁剧本拆为两份 md（b38f0e0），`run_synth.py` 一次生成两份产物、`actions.py` 抽出 `build_destroy_script` 独立骨架
- **task-20b 合并（codex 实现）**：合成剧本载体从 JSON 改为 Markdown 单源 —— 自研 540 行 stdlib YAML 解析器（不引新依赖）、frontmatter 装结构 + 正文按时间序铺事件/记录/actions、`script_io.validate_script` 在写库前断言事件引用与时间精度；新增 `template.md` 手写模板（可直接 replay）、9 项 pytest 覆盖 round-trip / 三类损坏剧本 / 模板可重放 / 编辑落库；IO seam 收敛在 `cli.py`，`actions.py / run_synth.py` 零改
- **task-21 任务卡入库**：PG 迁移 + Docker Compose，只换介质保留整库 dict 语义，application/domain/frontend 零感知；task-20 剧本作为跨 DB 一致性验收基线；同步顺手清理 task-20 四条遗留
- **task-20 合并（codex 实现）**：`tools/synth/` 落地 MiniMax-M2.5 合成流水（角色卡 / 时间线 / 延时表达行为），contextmanager 隔离 monkey-patch，`SYNTH_DB_PATH` 硬约束 + Assets 隔离，必经 application 层（含 `add_comment` 互动 / `start_uncouple` + `destroy_couple_data`），自带 3 项 pytest（分布 / 二次回放等价 / 生产路径拒绝）
- **task-13~19 A/B 级技术债 + task-12a/b UI 收尾**：详见 git log；契约收紧 / 校验加固 / Streamlit 废弃参数替换
- **v3.0.0 发布 + Phase 2 周报 v1**：DeepSeek pipeline / cron / UI 收尾 / Report 模型 / `destroy_couple_data` 联动
- **task-4~8 三视图与时间锁灵活化**：5 tab → 3 tab；`unlock_at` 自选；`pending_unlock` 流动性
- **早期里程碑**：v2.2.0 SQLite · v2.1.0 分层重构 · task-1~3 数据层

## 下一步（待决策 / 待启动）

> **战略转向 2026-05-13**：项目商业化路径锁定（微信小程序 + 云端），卖点回归延时表达本身，AI 暂缓到上市后。隐私底线提到端到端加密，详见 `docs/DIRECTION.md`。

1. **上线路线图已落定**：`docs/ROADMAP.md` 划分 5 个阶段（Alpha → UX 收尾 → 0→1 云端最小闭环 → 私测 → 公测/上市），每阶段标注卡点（用户解锁 vs 架构师驱动）。当前处于 **Phase 0**，下一步 Phase 1（架构师独立可推） + Phase 2 基础设施（待用户准备小程序 AppID + 云服务器）应并行
2. **Phase 1 启动信号待**：开始针对 Alpha Streamlit 上的延时表达 UX 列任务卡（写入流程 / 时间锁可视化 / 解锁瞬间 / 销毁链路 / 三视图切换 / 新手引导，详见 roadmap）；无外部依赖，用户给个 OK 就开干
3. **Phase 2 解锁待用户**：注册微信小程序 AppID（免费个人主体即可）+ 决定境内/境外云路线 + 租 VPS。这三件事不阻塞 Phase 1
4. **E2EE 协议已落定**：`docs/E2EE.md` 配对协议（X25519 ECDH + SAS）/ 密钥拓扑 / 双路恢复 / libsodium.js 选型 / 8 段实现里程碑就绪，等 Phase 2 启动按里程碑碾过
5. **task-21 / task-22 / 合成流水扩展 / Phase 2 周报 / 临时按钮清理**：全部冻结或顺延到对应 Phase；不在当前焦点

## 已知技术债 / 约束

- 详见 `docs/AUDIT.md`（Phase 2 周报 13 项）
- `tick()` 依赖页面加载触发，无独立调度器（部署期处理）
- `load_db()/save_db()` 整库读写，不适合多实例并发（部署期处理）

## 协作约定提醒

- 改 `backend/{application,infrastructure,domain,config}` 或 `frontend/streamlit_app` 前必读对应 `docs/api/*.md`，改动公开签名/语义后同步更新该 L2
- 任务卡只写 What 不写 How；Bug 只写症状由实现工自行诊断
- 本文件 ≤ 50 行，任务完成后由架构师维护
