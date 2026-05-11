# Task 6: UI 大改版 — 5 tab → 3 tab + 双向可见 bug 修复

**类型**：feature + bugfix（产品体验大改，含一个共享可见性 bug）
**Branch**：`codex/task-6`
**前置任务**：task-4 / task-5 已合并（依赖 `unlock_at` 字段与 pending_unlock 流动性动作）

## 背景

当前 5 tab 结构（「记录舱 / 灵感墙 / 已归档 / 情侣空间 / 账户」）有三个问题：

1. 「记录舱 / 灵感墙 / 已归档 / 情侣空间」是项目自创术语，新用户摸不着头脑
2. upload / pending / final 三个 tab 都属于「我自己的事」，被强行拆开，认知负担重
3. **「情侣空间」是单向可见 bug**：`tab_shared.py:24` 过滤条件用 `session.user_id == partner_id`，结果是自己 shared 给伴侣的内容在自己这边的「情侣空间」看不到，伴侣那边也只能看见我发的、看不见自己发的——和「双方共享空间」的产品定位相反

本任务把 UI 压到 3 tab，同时修复这个共享可见性 bug。**业务层零改动**，全部修改集中在 `frontend/` + `main.py`。

## 目标

顶层 3 个 tab：

| Tab | 替代的旧 tab | 显示内容 |
|-----|-------------|---------|
| 🏠 **我们** (默认落地页) | 旧「情侣空间」 | 整个 couple 内 `visibility=="shared"` 的全部 session，**包括自己 shared 的**；按 shared_at 倒序；自己/伴侣的卡片左右分边 |
| 📝 **我的** | 旧「记录舱 + 灵感墙 + 已归档」三合一 | 当前用户的全部 session，时间线倒序；每条卡片状态徽章一眼区分 4 种态 |
| ⚙️ **设置** | 旧「账户」 | 账户信息、伴侣绑定、冻结期、数据导出（行为不变，仅改名） |

## 改动范围

**许动**：

- `main.py`：tab 数量、名称、调度
- `frontend/streamlit_app/pages/`：
  - 新建 `tab_us.py`（我们）、`tab_mine.py`（我的）
  - 旧 `tab_upload.py` / `tab_pending.py` / `tab_final.py` / `tab_shared.py` 删除
  - 旧 `tab_account.py` 重命名为 `tab_settings.py`
- `frontend/streamlit_app/components.py`：状态徽章扩展、左右分边布局支持、`render_card` / `render_detail` 内部允许调整（含签名扩展）
- `docs/api/frontend_streamlit.md`：L2 契约大改
- 上传表单的字段编辑逻辑（原 `tab_upload.py` 主体）整体迁移到「我的」tab 的「写新记录」入口下，逻辑不变

**不许动**：

- `backend/**` 任何文件（业务层零改动）
- `backend/tests/`（业务层零改动则测试零失败；若改后失败说明业务被误碰，回退）
- `docs/STATUS.md` / `docs/CHANGELOG.md`（架构师维护）

## 接口约定

### 🏠 我们（`tab_us.py`）

- **过滤条件**：`session.couple_id == couple.couple_id AND session.visibility == "shared"`
  - 旧 `tab_shared.py` 的 `session.user_id == partner_id` 过滤是 bug，**本任务必须改成 `couple_id` 过滤，不再排除自己**
  - `can_view_session()` 已能正确处理双向，无需改 `backend/application/sessions/sharing.py`
- **排序**：按 `shared_at` 倒序
- **视觉规则**（iMessage 风左右分边）：
  - 自己（`session.user_id == 当前用户 user_id`）的卡片靠右
  - 伴侣的卡片靠左
  - 卡片顶部带作者用户名小徽章（区分作者）
  - 左右分边的具体实现（`st.columns` hack / CSS / 其他）由实现工自决
- **交互**：评论保留（情侣双向互动场所）；编辑 / 申请共享 / 撤回 / 追加 / 立即解锁 / 改时间等动作**不出现**在这里——这些都是「我对自己的记录的操作」，统一搬到「我的」detail 区
- **空状态**：
  - 未绑定伴侣 → 提示「先去『设置』里绑定伴侣」
  - 已绑定但 couple 内无 shared 记录 → 提示「还没有共享的记录，去『我的』写一条吧」

### 📝 我的（`tab_mine.py`）

- **顶部固定操作**：`[✍️ 写新记录]` 主按钮（具体是 expander 内展开 form 还是页内切到上传视图，实现工自决）
  - 表单字段集合、必填校验、文件上传、归档/暂存按钮的行为与旧 `tab_upload.py` 完全一致
- **过滤条件**：`session.user_id == 当前用户 user_id`，按 `upload_time` 或合理的时间字段倒序
- **状态徽章**（每条卡片右上角，4 种态）：
  - `status == "pending"` → `[草稿]`
  - `status == "final" AND visibility == "private"` → `[仅自己]`
  - `status == "final" AND visibility == "pending_unlock"` → `[倒计时·还有 N 天]`（沿用现有 `_days_until_unlock`）
  - `status == "final" AND visibility == "shared"` → `[已分享]`
- **detail 交互**：task-4 / task-5 提供的所有 session 操作都在此 tab 的 detail 展开里完成——
  - 草稿（`pending`）：继续编辑字段、转归档
  - 仅自己 / 已分享：编辑字段、申请共享 / 撤回（按当前 visibility 上下文显示对应动作）
  - 倒计时中（`pending_unlock`）：4 个动作完整保留（追加内容 / 修改时间 / 立即解锁 / 撤回；带 task-5 既定的二次确认约束）

### ⚙️ 设置（`tab_settings.py`）

- 行为与旧 `tab_account.py` 完全一致，仅改名 + 改 tab 标题文案
- 文案：从「⚙️ 账户」改为「⚙️ 设置」

### 状态徽章 helper

- 在 `components.py` 中扩展或新增 `_status_badge(session: SessionRecord) -> str`（命名可微调，语义不可变）：根据 `status` + `visibility` 返回上述 4 种徽章文案
- 旧 `_visibility_badge` 是否保留 / 改写 / 删除由实现工自决

## 验收行为（用户视角）

`uv run streamlit run main.py` 跑通：

- 登录后**默认落地在「🏠 我们」**（不是「我的」）
- 双向可见正确性：我发一条 + 申请共享立即解锁 → 我在「我们」看到这条靠右；伴侣登录后在自己的「我们」也看到这条靠左；伴侣再发一条立即解锁 → 双方都能看到 2 条
- 隐私不泄露：private / pending_unlock 状态的 session **不出现**在「我们」
- 「📝 我的」里看到自己全部 session，徽章 4 种态对应正确
- 点开 `pending_unlock` 的某条 → 4 个动作（追加 / 修改时间 / 立即解锁 / 撤回）完整可达，task-5 的二次确认约束生效
- 点开 `pending` 的某条 → 继续编辑字段、转归档
- 点「✍️ 写新记录」→ 与旧 upload tab 行为一致地完成一条记录
- 「⚙️ 设置」可发起绑定 / 接收绑定请求 / 解绑 / 冻结期导出，与旧「账户」一致
- UI 上不再出现「记录舱」「灵感墙」「已归档」「情侣空间」「账户」5 个旧词
- 未绑定伴侣时，「我们」给出引导文案而非空白

自动化检查：

- `uv run python -c "import backend, frontend; print('OK')"`
- `uv run pytest` 全绿（业务层零改动，原测试不应失败）
- `uv run ruff check .` 无错

## 已知陷阱

- 「我们」需要双向显示，但 `can_view_session(session, viewer_id)` 对 owner 始终返回 True，所以 owner 的 shared session 可见。**不要**为了维持「只看对方」的旧错误语义去绕过 `can_view_session`，直接走「couple_id + visibility==shared」即可
- 上传表单迁移时注意：旧 `tab_upload.py` 用了 `st.session_state` 的一些键来管理表单状态，迁移到「我的」tab 顶部后这些键不要和「我的」时间线的 expanded state 冲突
- 左右分边在 Streamlit 里通常用 `st.columns([1, 1])` + 留空一列实现，移动端宽度小的时候可能拥挤——alpha 阶段以桌面体验为准，不必为窄屏特意优化

## 必读契约

- `docs/api/frontend_streamlit.md`（当前 5 tab 结构、render_card / render_detail 公开形态）
- `docs/api/app_sessions.md`（sharing / editing 当前函数集；本任务不会改它们，但要知道 detail 区调用的是哪些）
- `docs/api/domain_models.md`（`SessionRecord` 字段含 `visibility` / `status` / `unlock_at` 等）

## 文档同步

- `docs/api/frontend_streamlit.md` 大改：tab 结构从 5 改 3，新增「我们」的过滤规则与左右分边约束、「我的」的状态徽章规则、`tab_settings` 改名
- 其他 L2 契约（`app_sessions.md` / `domain_models.md` / `app_maintenance.md` / `infra_db.md` / `config.md`）**不动**（业务层未改）
- `docs/STATUS.md` 与 `CHANGELOG.md` 不动（架构师维护）
