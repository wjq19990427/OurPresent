# Task 25: Phase 1 W2 · 冻结期销毁完整链路 UX

## 变更说明

类型：新功能 + 优化（用户可见）

把"决定分开 → 进入冻结期 → 90 天等待 → 自动销毁"这个最高敏感的流程做成**可二次确认、可双方反悔、双方可见**的完整 UX。当前缺四件事：进入冻结期没有二次确认；进入后没有任何撤回路径；伴侣端不知道对方按下了冷静键；以及一个仅靠前端反悔会带来的新问题——**如果撤回只需一方同意，另一方会被迫永久绑定**。本卡补完，并把整条链路的语气基调统一为「温柔但清醒」。

**语气基调（贯穿整张卡）**：温柔但清醒。不威吓 / 不悲情 / 不浪漫化分手 / 不重复说"应用只读"四遍。像一位信任的朋友在你最不冷静的时刻给你冷静的建议。所有 banner、二次确认面板、撤回三态文案、告别页都遵循这个基调。

**撤回的协议设计**：进入冻结期 = **单方可触发**（每个人都有权利按下冷静键）；撤回冻结期 = **必须双方同意**（避免任何一方被迫永久绑定）。两个非对称的方向都是有意的产品决策。

---

## 背景

`docs/ROADMAP.md` Phase 1 候选第 4 项落地。本卡是 Phase 1 三张串行卡（W1/W2/W3）中的第二张。

**现状摘录**（实现工可读代码确认）：

- `frontend/streamlit_app/pages/tab_settings.py` 191-214：解除绑定 expander 有「进入冻结期」/「双方同意立即销毁」两个按钮，**点击立即生效**，无二次确认
- 同上 216-239：冻结期 settings UI 仅展示到期时间 + 数据导出，**没有"撤回"入口**
- `backend/application/couples/uncoupling.py`：`start_uncouple(user_id)` / `confirm_uncouple(user_id)` / `is_frozen(user_id)` 已就绪；**完全缺撤回协议**（请求 / 同意 / 拒绝 / 自撤 四个动作都没有）
- `backend/domain/models/couple.py` 字段就绪：`couple_status` / `uncouple_initiated_by` / `uncouple_initiated_at` / `freeze_ends_at` / `both_agreed_uncouple`
- `backend/application/maintenance/ticking.py` 检测 `freeze_ends_at` 触发自动销毁，已就绪
- 已有二次确认模式可以参考：`render_comments` 中评论删除的 `pending_delete_*` 状态机

## 要做的改动

1. **进入冻结期 · 二次确认**：「进入冻结期」按钮改为两步确认（参考评论删除的 `pending_*` 状态机）。确认面板文案克制——不要"确定吗？" 这种工程感，也不要威吓口吻。给用户最后一次冷静的机会
2. **撤回冻结的双方握手协议**（**核心新功能**）：撤回不能单方决定——否则一方坚持反悔会让另一方被迫永久绑定。改造为请求-确认机制：
   - **domain**：`Couple` 新增字段 `cancel_uncouple_requested_by: str | None` + `cancel_uncouple_requested_at: str | None`，同步更新 `from_dict` / `to_dict`
   - **application**（4 个新公开函数 + 对应 `ensure_can_*` 校验）：
     - `request_cancel_uncouple(user_id)`：冻结期内任一方发起撤回请求 → 写入两个 `cancel_uncouple_requested_*` 字段；若已有 pending 请求则抛 `CoupleError`
     - `confirm_cancel_uncouple(user_id)`：对方同意 → `couple_status` 回到 `active`，清除所有冻结相关 + 请求相关字段；调用者必须是非发起方
     - `reject_cancel_uncouple(user_id)`：对方拒绝 → 仅清除请求字段，关系仍冻结；调用者必须是非发起方
     - `withdraw_cancel_request(user_id)`：发起方主动撤销自己刚提的请求 → 仅清除请求字段；调用者必须是请求发起方
   - **应用层导出**：`backend/application/couples/__init__.py`
   - **pytest**：四条路径全覆盖（请求-同意 / 请求-拒绝 / 请求-发起方自撤 / 各非法状态校验）
   - **L2 同步**：`docs/api/app_couple.md` 加四个新函数；`docs/api/domain_models.md` 同步 Couple 字段
3. **撤回入口 UI（按状态三态）**：冻结期 banner 与 settings 入口随 `cancel_uncouple_requested_by` 状态切换：
   - **无 pending 请求**：双方都看到「撤回冻结」入口；点了进入二次确认 → 请求落库
   - **有 pending 请求 · 当前用户是发起方**：看到「已发出撤回请求 · 等待对方回应」状态 + 「撤回我的请求」按钮（二次确认）
   - **有 pending 请求 · 当前用户是接收方**：看到「对方想撤回冻结期，回到正常状态」+「同意撤回」「拒绝撤回」两个按钮（各自二次确认）。文案克制，不要"对方求你和好"的悲情感
   - 同意 / 拒绝 / 发起方自撤 三种结果都有相应 UI 反馈，并且 banner 状态实时切换
4. **双方端可见性 banner**：进入冻结期后，**发起方 + 接收方**都能在 Streamlit 顶部（或「我们」/「我的」tab 顶部）看到 banner：「你们处于冻结期，还有 N 天 · 数据将在到期后自动销毁」。发起方/接收方文案略有区分（"你按下了冷静键" vs "对方按下了冷静键"），不要任何责备口吻。banner 上根据撤回请求状态展示对应入口（第 3 项的三态切换都在这里发生）
5. **双方同意立即销毁 · 二次确认**：当前一键即销毁全数据，过于轻易。改为两步确认。文案要明确告知"销毁后无法恢复"
6. **销毁瞬间的 UX 转场**：当前销毁后只 `st.error("已销毁全部数据")` + 清 session 跳回登录，太冷冰冰。改为温柔克制的告别页（短文案 + 数据已不可恢复声明 + 自动跳回登录），不再停留在 settings tab
7. **冻结期只读态文案一致性**：复查 `tab_us` / `tab_mine` / `tab_settings` 在 `couple_status == "frozen"` 时的所有"只读"提示文案，统一基调（克制、不威吓、不重复说"应用只读"四次）；自动隐藏所有写入 / 编辑 / 申请共享 / 追加 / 立即解锁动作（已有逻辑复查即可）
8. **L2 文档同步**：`docs/api/app_couple.md` 加四个新公开函数 + 对应 `ensure_can_*` 校验；`docs/api/domain_models.md` 同步 `Couple` 新增字段；`docs/api/frontend_streamlit.md` 同步 settings tab + banner 三态行为
9. **`CHANGELOG.md` `[Unreleased]`**：1-2 句总结用户可见变化

## 涉及文件

- `frontend/streamlit_app/components.py`（如 banner / 撤回三态 UI 抽成共用 helper）
- `frontend/streamlit_app/pages/tab_settings.py`（确认流程、撤回三态入口、告别页、文案）
- `frontend/streamlit_app/pages/tab_us.py` + `pages/tab_mine.py` **或** `main.py`（banner 放置位置实现工自选，但必须双 tab 都可见）
- `backend/domain/models/couple.py`（新增 `cancel_uncouple_requested_by` / `cancel_uncouple_requested_at` 字段 + from_dict/to_dict）
- `backend/application/couples/uncoupling.py`（新增四个公开函数：request / confirm / reject / withdraw）
- `backend/application/couples/policies.py`（新增对应 `ensure_can_*` 校验）
- `backend/application/couples/__init__.py`（导出）
- `backend/tests/`（请求 / 同意 / 拒绝 / 发起方自撤 / 非法状态全覆盖）
- `docs/api/app_couple.md`
- `docs/api/domain_models.md`
- `docs/api/frontend_streamlit.md`
- `CHANGELOG.md`

## 验收（用户可见行为）

- 点「进入冻结期」→ 二次确认面板出现 → 确认后才生效；取消则关闭面板，关系仍为 active
- 进入冻结期后**双方** Streamlit 顶部 banner 立刻出现："你们处于冻结期，还有 N 天"，发起方 / 接收方文案略有区分
- A 点「撤回冻结」→ 二次确认 → B 立刻看到「对方想撤回冻结期」+ 同意/拒绝两个按钮；A 看到「等待对方回应 · 可撤回我的请求」
- B 同意 → 关系回到 active，数据完整保留，banner 消失
- B 拒绝 → 撤回请求消失，关系仍冻结，A 在 settings 看到状态恢复"无 pending 请求"，可再次发起
- A 在 B 还没响应前可主动撤销自己的请求 → 状态恢复"无 pending 请求"，关系仍冻结
- 任一方都无法靠点一下按钮强制另一方回到 active
- 冻结期内 `tab_us` / `tab_mine` 没有任何写入 / 编辑 / 申请共享 / 追加 / 立即解锁动作；所有提示文案体现"温柔但清醒"基调
- 点「双方同意立即销毁」→ 二次确认 → 进入告别页（不留在 settings tab）→ 自动跳回登录
- 后端 4 个新函数在非法状态下抛 `CoupleError`，pytest 全覆盖
- `docs/api/app_couple.md` / `docs/api/domain_models.md` / `docs/api/frontend_streamlit.md` 三处同步

## 不要做

- **不要修改"双方同意立即销毁"的协议本身**：当前 `confirm_uncouple` 是单方点击即触发，**这是 W2 范围外的更大设计变更**（真正双方握手协议）。本卡只在 UX 层加二次确认，不动 `confirm_uncouple` 的后端语义
- **不要修改 `ticking.py` 的自动销毁逻辑**——`confirm_cancel_uncouple` 只清理冻结相关 + 请求相关字段，自动销毁条件自然失效
- **不要让撤回冻结变成单方动作**——双方握手是本卡的核心产品决策；如果实现工觉得"麻烦"想简化成单方撤回，必须先回来讨论
- **不要触碰 `docs/STATUS.md`、`docs/DIRECTION.md`、`docs/ROADMAP.md`、`docs/E2EE.md`、`docs/PRD.md`、`CLAUDE.md`**——架构师独占
- 不要做新手引导、三视图信息架构重组（W3 范围）
- 不要做"账号删除"或其他销毁路径（本卡范围只在 couple 冻结期销毁）
- 不要引入第三方依赖 / 自定义 CSS / Streamlit components
- 不要在 banner 用威吓 / 情绪化文案（"你确定要分手吗？！"），保持产品克制基调

## 提交规约

- `pytest backend/tests/` 整库通过（含新增四个撤回函数的全路径覆盖）
- `ruff check .` 通过
- 自行启动 Streamlit 验收，**端口必须指定非默认值**（默认 8501 大概率被架构师本机占用），例如 `streamlit run main.py --server.port 8765`
- **必须用两个账号**（一个发起方 / 一个接收方）分别验收冻结流程全链路：进入 → banner 出现 → 撤回 → banner 消失 → 数据完整；以及进入 → 双方同意立即销毁 → 告别页
- commit message 形如 `ux(freeze): 冻结期销毁完整链路 · 关联 #25`，可拆多个 commit
