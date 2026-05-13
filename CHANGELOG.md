# Changelog

所有版本的功能修改和更新记录。版本号格式：`主版本.次版本.补丁`。

---

## [Unreleased]

### PG 迁移启动

- **task-21 任务卡入库**：PostgreSQL + Docker Compose 介质迁移设计落定，整库 dict 语义保留，application/domain/frontend 零感知，task-20 合成剧本作为跨 DB 一致性验收基线；同步搭车清理 task-20 四条遗留

### 合成剧本生成端重构启动

- **task-20c 任务卡入库**：persona 改"一份 JSON = 一对情侣"、`run_synth.py` 一次输出一份剧本、结局（在一起 / 销毁）由 LLM 在生成时动态判断写入剧本 frontmatter；离线 fallback 读 persona 的 `expected_outcome`，CLI `--outcome` 可显式覆盖；与 task-21 核心文件零交集，可并行 Wave 1

### 合成剧本可读性优化启动

- **task-20b 任务卡入库**：合成剧本载体由 JSON 改为 Markdown 单源，frontmatter 装结构、正文按时间序铺事件与延时行为；新增手写模板供使用者直接填充并 replay，driver/replay 仅换 IO 层，业务零改；与 task-21 核心文件不冲突，并行 Wave 1
- **task-20b 实现**：`tools/synth/scripts/任务20_合成数据剧本.md` 成为入库样例，`script_io` 在写库前校验 frontmatter、事件引用、记录字段和行为时间精度；新增 `template.md`，文档补齐“重放”“frontmatter”“公开状态”“actions”等定义，方便非工程使用者直接阅读和手改剧本。
- **task-20b 样例拆分**：主剧本只保留一对情侣的延时共享故事，关系解除与销毁链路拆到 `任务20_销毁链路剧本.md`；`run_synth.py` 会生成两份 Markdown 并在同一个隔离运行上下文内写库，避免跨剧本 UUID 重置。
- **task-20b 后续修复**：session `created_at` 严格对齐事件日期 + 销毁样例语义/时间修正 + 主线 / 销毁线拆为两份独立 md 剧本（02c6b6e / be04208 / b38f0e0）。

### 合成数据 workflow 落地

- **task-20**：`tools/synth/` 独立工具链上线 —— MiniMax-M2.5 驱动「角色卡 / 时间线 / 延时表达行为」三层合成，contextmanager 隔离 monkey-patch、`SYNTH_DB_PATH` + Assets 双重隔离、必经 application 层（含 `add_comment` 互动 / 销毁链路），剧本支持无 LLM 重复写库，自带 3 项 pytest（分布 / 二次写库等价 / 生产路径拒绝）

### Phase 2 周报 B 级技术债清理（对应 `docs/phase2_audit.md` B3/B4/B5/B6）

- **task-16（B3）**：`_load_dotenv_api_key` 改 walk-up 找 `pyproject.toml`，解除 `parents[3]` 硬编码；找不到项目根时静默跳过
- **task-17（B4）**：`get_report_history(couple_id, include_failed=False)` 显式参数化，默认与 UI 渲染语义对齐过滤 `failed`，避免失败报告污染未来智能体上下文
- **task-18（B5）**：guard 新增 `blocked_user_ids` 形参；扫描范围扩展至 `weather.narrative` / `weather.tags.*` / `resonance.day` / `topic` / 双方 excerpt，命中真实 user_id 直接判 failed
- **task-19（B6）**：`_session_day` 主路径与 fallback 共用 `YYYY-MM-DD` strptime 校验，无效日期 session 不再进入 resonance 配对

### UI 一致性收尾

- **task-12a**：全量替换 Streamlit 已废弃的 `use_container_width` 参数（→ `width='stretch' / 'content'`），消除启动告警
- **task-12b**：登录页迁移至单列移动端风格，视觉语言与认证后「我的 / 我们 / 设置」三个 tab 对齐

### Phase 2 周报 A 级技术债清理（对应 `docs/phase2_audit.md` A2/A3/A4）

- **task-13（A2）**：`compute_footprint` 输入契约收紧，缺失或无法解析 `shared_at` 直接抛 `ValueError`，把隐私边界从跨模块约定升级为运行期断言
- **task-14（A3）**：`extract_semantic(sessions, couple)` 接收 Couple 上下文；resonance 候选严格按 `Couple.user_a` / `Couple.user_b` 对位，不再依赖 user_id 字典序，消除「我们」tab 周报左右两侧作者错位
- **task-15（A4）**：`DEEPSEEK_BASE_URL` 启动期强制校验 https scheme，否则抛 `LLMClientError`；错误信息不回显环境变量内容，避免污染日志

## [v3.0.0] - 2026-05-11

### Phase 2 · AI 情感周报上线（核心）

阶段性里程碑：第二阶段第一个 AI 模块完整落地。本版本将 Phase 2 第一个智能体（情感周报）从设计稿推到端到端可用，是项目从「双人记录工具」迈向「客观情感记录者」的关键一步。

**功能**

- **NVC 四模块周报**：关系足迹 / 情绪气象 / 同频共鸣 / 未尽悬念，温和陈述不评判，不替任何一方下判断
- **双方协议制服务开关**：双方都在「设置」开启「情感周报服务」才生成；未开启侧文案温和邀请，不催促
- **频率可调**：couple 级共享配置 `weekly_report_interval_days`，默认 7 天，可选 7 / 14 / 30
- **自动触发**：`tick()` 按节律自动生成；上次失败下次重试一次；冻结期跳过
- **数据稀疏兜底**：窗口内 < 3 条共享时生成 sparse 报告（仅 footprint），不调 LLM，UI 给温和说明
- **历史可读**：「设置 → 查看周报历史」展示所有 ready / sparse 报告

**隐私三层约束**

1. **数据访问**：唯一入口 `get_shared_sessions_for_rag(couple_id, window)`，永不读 private / pending_unlock
2. **LLM 输入字段白名单**：`description / feeling / content_time / user_id`，不传 `session_id` / 文件路径 / `couple_id`
3. **反原文引用兜底**：LCS 阈值 12 字符，命中则 report 标 `status="failed"` 不展示

**工程**

- LLM 接入：DeepSeek V4 Flash，裸 urllib + 手写 `.env` 解析，零额外依赖
- 新模块：`backend/application/reports/{metrics,policies,query,semantic,guard,generate,scheduling,errors}.py` + `backend/infrastructure/ai/llm_client.py`
- 新表：`reports`（JSON blob 拆 4 列），`User.weekly_report_enabled` / `Couple.weekly_report_interval_days` 经 `_migrate_db` ALTER 兼容旧库
- `destroy_couple_data` 联动清理 reports，关系结束时不留残余
- 测试覆盖：57 个新增测试用例，含「字段白名单隐私验证」spy 测试与「旧 schema 升级路径」迁移测试
- 临时调试入口「🧪 立即生成周报」保留至 cron 验证稳定，将由架构师另开任务删除

**文档**

- 新增 `docs/AI.md` 产品愿景（NVC 镜子定调）
- 新增 `docs/weekly_report.md` 工程设计稿（Pipeline 七阶段 / 隐私三层约束 / 8 项决策闭环）
- 新增 `docs/phase2_audit.md` Opus 复审技术债清单（13 项）
- 新增 `docs/api/app_reports.md` / 扩展 `docs/api/infra_ai.md`
- 同步更新 README / PRD / ARCHITECTURE / state-machines / user-guide / extension-guide

**已知技术债（已记入 `docs/phase2_audit.md`，不阻断本次发版）**

- `tick()` → `generate_weekly_report` 嵌套 `load_db/save_db` 的非原子风险
- `compute_footprint` 对缺失 `shared_at` 的静默放行
- `resonance` user_a/b 列与 `Couple.user_a/b` 字典序非对齐
- `DEEPSEEK_BASE_URL` 缺少 `https://` 强制校验
- guard 阈值 12 字符为经验值，待真实语料校准

## [v2.4.0] - 2026-05-11

### UI 大改版（核心）

- 顶层从 5 tab 压成 3 tab：旧「记录舱 / 灵感墙 / 已归档 / 情侣空间 / 账户」合并为「🏠 我们 / 📝 我的 / ⚙️ 设置」，默认落地「我们」
- UI 上不再出现项目自创术语，新用户上手心智模型对齐主流社交媒体
- 卡片状态徽章统一为 4 态：`[草稿] / [仅自己] / [倒计时·还有 N 天] / [已分享]`，`status × visibility` 二维状态一眼可读
- 「我的」承接全部「我对自己记录的操作」：写新记录（顶部 `✍️` 入口）、继续编辑草稿、申请/撤回共享、追加内容、修改开放时间、立即解锁
- 「设置」文案去掉「我要分手」「分手协议」等情绪化用词，更克制

### 共享双向可见 bug 修复

- 旧「情侣空间」用 `session.user_id == partner_id` 过滤，结果自己 shared 给伴侣的内容在自己这边看不到，伴侣那边也只能看见我发的、看不见自己发的——与「双方共享空间」的产品定位相反
- 新「我们」改为 `couple_id + visibility == "shared"` 过滤，自己/伴侣的 shared 记录在双方时间线上都可见；iMessage 风左右分边（自己靠右、伴侣靠左），卡片顶部带作者徽章
- 「我们」详情区只读展示字段和文件，评论区仍可双向互动；编辑/分享/撤回等动作只在「我的」detail 区出现

### 工程收尾

- `render_detail.selected_state_key` 改为 keyword-only 必填，删除两个永远不命中的 fallback；L2 契约同步
- 登录页「⏳ 授权后满 90 天」改为「⏳ 申请共享时自定开放时间」，对齐 v2.3.0 之后的真实机制
- 业务层零改动，全部修改收敛在 `frontend/` + `main.py` + 3 份 L2 契约（`frontend_streamlit.md` / `main.md` / `domain_models.md`）

## [v2.3.0] - 2026-05-11

### 时间锁灵活化（核心）

- 共享时间锁从固定 90 天改为用户自选：申请共享时可选立即 / 1 天 / 3 天 / 1 周 / 1 个月 / 90 天 / 日历自定义日期，默认 1 周
- `SessionRecord` 新增 `unlock_at` 字段，`tick()` 基于 `unlock_at` 判定推进，`upload_time` 不再参与共享解锁计算
- pending_unlock 阶段的流动性增强：申请共享后仍可追加文本内容（保留原文 + 「追加于 时间」分隔标记，不写编辑历史）、修改开放时间、立即解锁、撤回共享
- UI 上「修改开放时间」与「立即解锁」必须勾选二次确认，明确告知会改变伴侣看见时刻，避免时间锁形同虚设
- 「shared 时 unlock_at == shared_at」作为跨函数不变量统一固化（`request_unlock` 立即-分支、`unlock_now`、`reschedule_unlock` 三路径对齐）

### 本地阶段收尾

- session 子域类型边界贯穿到 UI：`application/sessions/*` 与 `frontend/streamlit_app/*` 公开签名全面 `dict` → `SessionRecord`，dict↔dataclass 转换严格收敛在 `sessions_repo` 持久化边界
- 密码哈希从 SHA-256 + 固定盐切换到 bcrypt（独立盐 + 自适应代价因子），旧哈希兼容彻底删除
- 删除旧 JSON 库迁移过渡路径：`db.py` 不再嗅探 `data/db.json`，`LEGACY_DB_PATH` 常量移除，持久化单一锚定 SQLite
- 引入 `_migrate_db` + `_ensure_column` 轻量 ALTER TABLE 模式承载 schema 演进（alpha 阶段权宜，未来需清算）

### 文档与叙事

- README 理念叙事整理：保留延时表达作为灵魂卖点，删除主题重复表述；「Present 三层含义」与「当前能力」拆为独立小节，各能力补一句价值描述
- L2 契约（`docs/api/*.md`）随每个任务同步更新；任务卡（`docs/tasks/task-1..5.md`）入库
- 新增 `docs/STATUS.md` 项目状态快照，由架构师维护「最近完成 / 下一步 / 已知技术债」

## [v2.2.0] - 2026-05-09

### 存储升级

- 底层持久化从 `data/db.json` 升级为 SQLite，默认数据库文件改为 `data/database.db`
- 启动时如果检测到旧版 `data/db.json` 且 SQLite 为空库，会自动执行一次迁移导入
- 保留现有 `load_db()` / `save_db()` 的上层调用方式，减少对业务层和 UI 层的影响

### 文档与验证

- 同步更新 README、技术文档和 `AGENTS.md`，说明新的数据库路径与迁移行为
- 补充存储层测试，覆盖空库初始化、旧 JSON 迁移和 SQLite 持久化
- 验证通过：`uv run ruff check backend main.py frontend`、`uv run pytest`

## [v2.1.0] - 2026-05-07

### 重构（无新功能）

核心目标：

- 把 `application` 从“大文件堆功能”改成按业务能力分组
- 把 `database` 从一个混合式 `db_manager.py` 改成仓储拆分
- 为后续继续收紧类型边界，引入 `domain/models` dataclass
- 让文档描述与当前真实代码结构重新一致

### 当前目录结构（重构完成后）

```text
backend/
├── api/
├── application/
│   ├── auth/
│   ├── couples/
│   ├── maintenance/
│   └── sessions/
├── config/
├── domain/
│   └── models/
└── infrastructure/
    ├── ai/
    ├── database/
    └── media/

frontend/
└── streamlit_app/
    ├── components.py
    └── pages/
```

### application 层职责重组

`backend/application/` 不再按“技术名词大文件”组织，而改为按业务能力和用例边界拆分：

- `auth/`
  - `commands.py`：注册、登录
  - `tokens.py`：持久化登录 token 的创建、恢复、撤销
  - `errors.py`：`AuthError`
- `couples/`
  - `policies.py`：绑定、解绑前的业务规则校验
  - `binding.py`：发送绑定请求、接受、拒绝
  - `uncoupling.py`：冻结期解绑、双方同意销毁、冻结状态判断
  - `errors.py`：`CoupleError`
- `sessions/`
  - `creation.py`：新建待处理 / 直接归档
  - `editing.py`：字段编辑、待处理转归档
  - `sharing.py`：可见性判断、申请共享、撤回共享
  - `comments.py`：评论新增、删除
  - `export.py`：导出文件收集
  - `destruction.py`：按情侣关系销毁数据
  - `validation.py`：纯文字记录判断、必填字段校验
  - `files.py`：session 附件命名、写入、删除
  - `markdown.py`：归档 Markdown 生成
- `maintenance/`
  - `ticking.py`：时间锁推进、冻结期到期销毁、过期 token 清理

这次调整的核心是让每个文件只回答一个问题：

- 怎么注册和登录
- 怎么绑定和解绑
- 怎么创建记录
- 怎么编辑记录
- 怎么推进状态

这样后续继续扩展时，不会再把认证、session、情侣关系和系统维护逻辑重新缠在一起。

### infrastructure/database 重组逻辑

原来的 `db_manager.py` 同时承担了：

- DB 文件读写
- 时间工具
- 密码哈希
- User CRUD
- Couple CRUD
- Token CRUD

这会让 application 层虽然表面拆了目录，实际上仍然都直接贴着一个“万能数据库文件”。

本次改为：

- `db.py`
  - 只负责 `load_db()`、`save_db()`、`ensure_dirs()`、`now_str()`、`parse_dt()`
- `users_repo.py`
  - 用户创建、查找、密码校验、用户更新
- `couples_repo.py`
  - 情侣关系创建、查找、接受请求、拒绝请求、关系更新
- `sessions_repo.py`
  - session 的增、查、替换
- `tokens_repo.py`
  - 登录 token 的创建、校验、撤销

这一步的意义是把“业务规则”和“持久化接口”拆开：

- repository 只负责存取
- application 负责规则和流程

### domain/models 引入 dataclass

新增：

- `User`
- `Couple`
- `SessionRecord`
- `AuthToken`

这些 dataclass 解决两个问题：

- 到处传裸 `dict`，字段边界太松
- 上层调用不容易区分“这是用户”“这是情侣关系”“这是 token”

当前每个模型都提供：

- `from_dict(data)`
- `to_dict()`

这让 JSON 持久化结构和业务对象之间有了明确转换边界。

本次落地情况：

- 认证链路已切到 `User` / `AuthToken`
- 情侣关系链路已切到 `Couple`
- session 创建与 repository 已切到 `SessionRecord`
- 前端渲染层仍保留部分 session dict 访问，降低本轮重构风险

也就是说，这次是“先把类型边界建立起来”，而不是一步到位把整个 UI 层都改成完整对象流。

### 文件与媒体职责调整

原 `infrastructure/utils/io.py` 中同时混有：

- session 附件写入
- 文件名清洗
- 视频缩略图
- PIL 图片转换

本次按职责拆开为：

- `backend/application/sessions/files.py`
  - `write_session_files()`
  - `delete_session_files()`
  - `_safe_filename()`
- `backend/infrastructure/media/thumbnails.py`
  - `video_thumbnail()`
  - `pil_to_png_bytes()`

调整原则：

- 明显带有 session 语义的文件操作，上移到 `application/sessions`
- 可复用的媒体预览能力，保留在 `infrastructure/media`

### 前端边界同步

本次同步调整了 `main.py` 与 `frontend/streamlit_app/` 的依赖方向：

- 登录恢复改为通过 `application.auth.tokens`
- 冻结期状态改为通过 `application.couples`
- 用户、情侣关系查询改为通过拆分后的 repository
- `components.py` 中的 `_current_user()`、`_couple()`、`_partner_id()` 开始使用 `User` / `Couple`

这样前端依赖关系也更清晰：

- 业务动作优先走 `application`
- 查询型读取可以少量直连 repository
- 页面层不再直接碰旧的“全功能 DB 管理器”

---

## [v2.0.1] - 2026-05-05

### 清理

- 移除重构前遗留的 `app.py`、`db.py`、`auth.py`，统一以 `main.py` 作为 Streamlit 入口
- 统一界面和占位配置命名为 OurPresent
- 更新 README / PRD 中的项目结构与模块引用，避免新旧架构说明混杂

---

## [v2.0.0] - 2026-04-30

### 重构（无新功能）

**代码目录结构拆分**：将原有 `app.py` + `db.py` + `auth.py` 三文件架构，按职责拆分为以下模块：

```
core/
  config.py          # 路径常量、TEXT_EXTS、TOKEN_EXPIRE_HOURS、FIELD_SCHEMA
  state_machine.py   # tick()、load_db_with_tick()
  agent_skills.py    # Phase 2 LLM 接口占位

utils/
  validators.py      # _is_text_session()、validate_session()
  file_processor.py  # write_files()、video_thumbnail()、pil_to_png_bytes()

backend/
  db_manager.py      # JSON 读写、User/Couple CRUD、登录 Token 管理
  session_manager.py # Session 生命周期、评论、可见性控制、数据销毁、解绑协议
  auth_manager.py    # 注册/登录/绑定业务校验（AuthError、CoupleError）

frontend/
  components.py      # 会话工具、显示辅助、字段渲染、卡片、详情区、评论区
  pages/
    tab_upload.py    # Tab 1 — 记录舱
    tab_pending.py   # Tab 2 — 灵感墙
    tab_final.py     # Tab 3 — 已归档
    tab_shared.py    # Tab 4 — 情侣空间
    tab_account.py   # Tab 5 — 账户设置

main.py              # 入口：_init_state()、render_auth_page()、main()
```

**变更细节**

- 所有路径常量和 `FIELD_SCHEMA` 集中到 `core/config.py`，消除跨模块重复定义
- `_is_text_session` / `validate_session` 移至 `utils/validators.py`，可独立单元测试
- `_write_files` 重命名为 `write_files`（公开函数），与视频缩略图工具同移至 `utils/file_processor.py`
- `initiate_uncouple` / `agree_uncouple` / `destroy_couple_data` 从 `db.py` 移至 `backend/session_manager.py`，与 Session 生命周期管理统一
- `tick` / `load_db_with_tick` 单独提取为 `core/state_machine.py`，职责更清晰
- 原 `app.py` 中的 Tab 渲染函数各自独立为 `frontend/pages/tab_*.py`
- 入口由 `app.py` 改为 `main.py`，启动命令更新为 `python -m streamlit run main.py`
- 旧的 `app.py`、`db.py`、`auth.py` 已移除，避免新旧入口并存造成维护混乱

**依赖层次（无循环导入）**

```
core/config → utils → backend/db_manager → backend/session_manager
→ backend/auth_manager → core/state_machine → frontend → main.py
```

---

## [v1.2.0] - 2026-04-24

### 新增

- **持久化登录状态**：登录成功后在 `data/db.json` 的 `auth_tokens` 表写入 UUID token，并通过 `st.query_params["token"]` 将 token 写入 URL
  - 刷新页面时 `_init_state()` 读取 URL 中的 token 并自动校验恢复登录，无需重新输入账号密码
  - Token 默认有效期 **24 小时**，到期后刷新页面自动跳转至登录页
  - 退出登录时同步从 DB 中撤销 token 并清除 URL 参数
  - `db.tick()` 每次加载时自动清理所有已过期 token

- **两标签页测试兼容**：每个浏览器标签页拥有独立的 `st.session_state` 和 URL query param，Tab 1 登录用户 A、Tab 2 登录用户 B 互不干扰，行为与修改前完全一致

### 变更

- `data/db.json` 顶层新增 `auth_tokens` 数组，自动兼容旧格式（读取时若字段缺失则补全为空数组）
- `db._EMPTY_DB` 补充 `auth_tokens` 初始键

### 新增函数（`db.py`）

| 函数 | 说明 |
|------|------|
| `create_auth_token(user_id)` | 创建 token，写入 DB，返回 token 字符串 |
| `validate_auth_token(token)` | 校验 token 有效性，返回 user 记录或 None |
| `revoke_auth_token(token)` | 使 token 失效（退出登录时调用） |

---

## [v1.1.0] - 2026-04-24

### 修复

- **情侣绑定确认 UI 逻辑错误**：`pending_bind` 状态下，接收方和发送方共用同一段提示文案"等待对方确认中……"，导致接收方误以为无需操作，忽略上方的接受/拒绝按钮
  - 修复：区分发送方（`couple["user_a"] == 当前用户`）和接收方，分别展示不同提示
  - 发送方：显示"已向 XXX 发出绑定请求，等待对方确认……"
  - 接收方：显示醒目黄色警告"👆 请在上方「收到的绑定请求」区点击接受或拒绝"

---

## [v1.0.0] - 2026-04-24

### 新增（首个可运行版本）

**架构重构（基于早期单人记录 Demo 演进）**

- 从单人单文件架构重构为三层模块化架构：
  - `db.py`：数据层，负责所有磁盘 I/O 和状态机推进
  - `auth.py`：鉴权层，负责注册/登录/情侣绑定/解绑协议
  - `app.py`：UI 层，全部 Streamlit 页面渲染

**多用户系统**

- 注册/登录页（用户名 + 密码，SHA-256 哈希存储）
- 每位用户生成唯一 `user_id`（`usr_` + 8位 UUID hex）
- `data/db.json` 替换 `pending_db.json`，顶层从 JSON 数组升级为对象，包含 `users`、`couples`、`sessions` 三张表

**情侣绑定系统**

- 通过 `user_id` 搜索伴侣并发起绑定请求（`pending_bind` 状态）
- 被邀请方在「账户」页确认或拒绝，确认后状态升级为 `active`
- 绑定后双方共享同一 `couple_id`，数据按此字段关联

**权限状态机（时间锁）**

- Session 新增 `visibility` 字段，三态：`private` → `pending_unlock` → `shared`
- 创建时默认 `private`，仅创建者可见
- 用户手动申请共享：写入 `unlock_requested_at`，状态变为 `pending_unlock`
- `db.tick()` 在每次页面加载时运行：满 90 天后自动推进至 `shared`，写入 `shared_at`
- 支持在 `pending_unlock` 阶段撤回申请，恢复为 `private`

**分手协议与数据冻结**

- 单方发起解绑：`couple_status` 变为 `frozen`，记录 `freeze_ends_at`（90 天后）
- 冻结期内应用全局只读，上传/编辑入口均禁用
- `db.tick()` 到期自动调用 `destroy_couple_data()`，删除双方全部 sessions 和文件
- 双方同意解绑：调用 `agree_uncouple()`，立即销毁，无需等待冻结期
- 冻结期内支持数据导出：仅导出属于自己的文件，打包为 ZIP 下载

**数据隔离**

- 所有文件统一存放于 `Assets/Pending/` 和 `Assets/Final/`，不按用户分目录
- 数据层通过 `user_id` / `couple_id` 过滤，UI 层仅渲染当前用户的数据
- 情侣空间（Tab 4）仅展示伴侣 `visibility == "shared"` 的记录，调用 `can_view_session()` 二次校验

**强制文本描述（RAG 预备）**

- 文件型记录的 `description` 字段改为强制必填（`required=True`）
- 纯文字/文本文件记录保留自动填充逻辑，描述由内容自动写入
- Session 新增 `couple_id`、`user_id`、`visibility`、`unlock_requested_at`、`shared_at` 字段，为后期 RAG 向量化提供结构化 Metadata

**评论区扩展**

- 评论结构新增 `author` 字段，记录评论者 `user_id`
- 渲染时展示评论者用户名

**UI 新增 Tab**

- Tab 4「💌 情侣空间」：展示伴侣共享给自己的记录，只读查看
- Tab 5「⚙️ 账户」：用户信息、绑定请求收发、解绑协议、冻结期导出

### 变更

- `pending_db.json` 迁移为 `data/db.json`，顶层结构从数组变为对象
- `FIELD_SCHEMA` 中 `description` 的 `required` 字段从 `True`（仅文字必填）改为对所有 source_type 均必填；纯文字记录通过 `skip_keys` 机制绕过 UI 渲染，不破坏 Schema 定义
- Session `comments` 条目新增 `author` 字段（`user_id`）
- 文件存储路径 `Assets/` 目录结构不变，兼容早期 Demo 原有文件

### 已知限制

- `db.json` 为本地单文件，并发写入无锁保护，不适合多实例部署（Demo 阶段可接受）
- `db.tick()` 依赖页面加载触发，无独立定时任务；极端情况下冻结期到期但无人访问时不会立即销毁（安全方向保守，可接受）
- 密码哈希使用 SHA-256 + 固定盐，适合本地 Demo，生产环境应替换为 `bcrypt` 或 `argon2`
