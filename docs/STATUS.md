# 项目状态快照

**最后更新**：2026-05-17  ·  **当前版本**：**v3.1.0**（已发布）  ·  **阶段**：Phase 2 · M0 完成，M1/M2 Wave 1 并行进行中  ·  详见 `docs/PHASE2.md` / `docs/ROADMAP.md`

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

- **M0 完成（2026-05-17）**：`server/`（FastAPI + PG + Minio + Nginx Docker Compose 骨架 + Dockerfile + Nginx conf）+ `miniprogram/`（小程序 TS 骨架 + 分包结构占位）进 mono-repo；task-27（M1 客户端加密 smoke test）+ task-28（M2 服务端骨架）任务卡入库
- **task-26 合并（codex 实现）· Phase 1 W3**：farewell URL bug 修复（纯 session_state）；「我的」tab 分「等待开放」/「私密记录」两区含最快开放时间；绑定后首次引导；「我们」tab 未绑定空状态升级为卡片 + 一键跳设置；第一条 shared 记录 24h 魔法时刻；空状态文案全局统一
- **W2 后续补丁（`c79c0aeb` / `4875af4d`）**：① 未绑定用户写记录限制修复 + 删除未共享记录功能（`delete_session` 后端 + UI 二次确认 + 测试 + L2 文档）；② 冻结期新增「现在分手」双方握手协议（`destroy_uncouple_*` 字段四路函数，与撤回冻结并列）；告别页拆为独立 `pages/farewell.py`；主动检测 couple 解散后跳转告别页；⚠️ farewell URL query param 持久化有 bug，已列入 task-26 待修
- **task-25 合并（codex 实现）· Phase 1 W2**：冻结期销毁完整链路——进入冻结期 / 立即销毁改为二次确认；撤回冻结双方握手（request/confirm/reject/withdraw 四路）；全局顶部 banner 三态切换；销毁后告别页；文案统一「温柔但清醒」基调；domain 新字段 + DB 迁移 + L2 文档同步
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

1. **Wave 1 并行进行中**：
   - **task-28 · M2**（`server/`，可立即派发给实现工，无外部依赖）
   - **task-27 · M1**（`miniprogram/`，开发者工具部分可立即启动；真机验证等用户 AppID 到手）
2. **用户阻塞项**：小程序接口测试号 AppID（M1 真机验收必须，用户说"不得不用时再申请"）
3. **基础设施状态**：服务器（学长的，不用）· ICP 备案办理中（不阻塞 Phase 2）· 域名等备案下来 · 公司未注册（Phase 4 才需要）
4. **Wave 1 完成后**：M3 配对协议（依赖 M1 + M2 双双完成）
5. **task-21 / task-22 / 合成流水扩展 / Phase 2 周报**：全部冻结或顺延到对应 Phase

## 已知技术债 / 约束

- 详见 `docs/AUDIT.md`（Phase 2 周报 13 项）
- `tick()` 依赖页面加载触发，无独立调度器（部署期处理）
- `load_db()/save_db()` 整库读写，不适合多实例并发（部署期处理）

## 协作约定提醒

- 改 `backend/{application,infrastructure,domain,config}` 或 `frontend/streamlit_app` 前必读对应 `docs/api/*.md`，改动公开签名/语义后同步更新该 L2
- 任务卡只写 What 不写 How；Bug 只写症状由实现工自行诊断
- 本文件 ≤ 50 行，任务完成后由架构师维护
