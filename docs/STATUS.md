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

- **Phase 1 W1 UX 测试补丁（`08f86e7c` / `6418a295`）**：用户自测后 codex 跟进——`delete_comment` 后端加 `author_id` 强校验（35 新增测试）+ UI 二次确认；卡片预览改为 `_render_session_preview`（图片 / 视频内联 / 文字截断）；「我的」tab 过滤已共享记录、详情内嵌到卡片下、关闭详情区文件预览 panel 重复展示；`render_comments` 新增 `key_scope` 修复多处渲染时 widget key 冲突
- **task-24 合并（codex 实现）· Phase 1 W1**：写-锁-解锁主旅程——首条入口默认展开 + 字段重排；申请共享默认 1 个月；待解锁徽章改为「等待开放 · 还要 N 天/时/分」；伴侣端预告区块（只暴露数量+时间）+ 24h 「新近解锁」标识；评论区内嵌所属卡片 + visibility 三段可见度；「我们」tab 隐藏完整度提示 + 移动端作者归属标签
- **task-23 合并（codex 调研）**：微信小程序作为 E2EE 客户端的事实边界报告落盘 `docs/research/wechat-miniprogram-crypto.md`，覆盖加密 API / `wx.setStorage` / 钥匙丢失 / 包体积 / 性能 / 备份载体 / OOB 配对通道 8 个问题
- **task-20c 合并（codex 实现）**：合成生成端切到「一份 persona = 一对情侣 = 一份剧本」；`build_script(persona, timeline, outcome, ...)` 单一入口，结局由 LLM 输出 outcome/outcome_reason 写入 frontmatter；旧"任务20_*.md"产物按角色重命名
- **task-20b 合并（codex 实现 + 后续修复）**：合成剧本载体 JSON → Markdown 单源，自研 540 行 stdlib YAML 解析器；主剧本与销毁剧本拆为两份 md；9 项 pytest 覆盖 round-trip / 损坏剧本 / 模板可重放
- **task-21 任务卡入库（冻结）**：PG 迁移设计完成但暂不实施——E2EE 协议落定后服务端形态将变为「密文 BLOB + 明文元数据索引」，与本卡假设不兼容，留待 mini-program 工程启动时另写
- **task-20 合并（codex 实现）**：`tools/synth/` 落地 MiniMax 合成流水（角色卡 / 时间线 / 延时表达行为）
- **task-13~19 A/B 级技术债 + task-12a/b UI 收尾**：详见 git log；契约收紧 / 校验加固
- **v3.0.0 发布 + Phase 2 周报 v1**：DeepSeek pipeline / cron / UI 收尾 / Report 模型
- **早期里程碑**：v2.2.0 SQLite · v2.1.0 分层重构 · task-1~8 数据层与时间锁灵活化

## 下一步（待决策 / 待启动）

> **战略转向 2026-05-13**：项目商业化路径锁定（微信小程序 + 云端），卖点回归延时表达本身，AI 暂缓到上市后。隐私底线提到端到端加密，详见 `docs/DIRECTION.md`。

1. **Phase 1 W1 完成**（task-24 已合）。**W2 待开**：冻结期销毁完整链路（提示 → 反悔 → 销毁），主战场 `tab_settings` + 只读态。**W3 待开**：三视图信息架构 + 新手引导，跨三个 tab。串行执行，等用户 dogfood W1 反馈后开 W2
2. **Phase 2 基础设施进度**：服务器已租 ✓ · ICP 备案中 · 小程序 AppID 待办（建议用「接口测试号」开发期免主体）· 公司未注册（Phase 4 才需要）
3. **E2EE 协议已落定**：`docs/E2EE.md` 配对协议（X25519 ECDH + SAS）/ 密钥拓扑 / 双路恢复 / libsodium.js 选型 / 8 段实现里程碑就绪
4. **task-21 / task-22 / 合成流水扩展 / Phase 2 周报 / 临时按钮清理**：全部冻结或顺延到对应 Phase

## 已知技术债 / 约束

- 详见 `docs/AUDIT.md`（Phase 2 周报 13 项）
- `tick()` 依赖页面加载触发，无独立调度器（部署期处理）
- `load_db()/save_db()` 整库读写，不适合多实例并发（部署期处理）

## 协作约定提醒

- 改 `backend/{application,infrastructure,domain,config}` 或 `frontend/streamlit_app` 前必读对应 `docs/api/*.md`，改动公开签名/语义后同步更新该 L2
- 任务卡只写 What 不写 How；Bug 只写症状由实现工自行诊断
- 本文件 ≤ 50 行，任务完成后由架构师维护
