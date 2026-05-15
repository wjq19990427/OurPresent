# Task 25: Phase 1 W2 · 冻结期销毁完整链路 UX

## 变更说明

类型：新功能 + 优化（用户可见）

把"决定分开 → 进入冻结期 → 90 天等待 → 自动销毁"这个最高敏感的流程做成**可二次确认、可反悔、双方可见**的完整 UX。当前缺三件事：进入冻结期没有任何二次确认（点击即生效）、进入后没有任何方式撤回（除非默默等到 90 天）、伴侣端不知道对方按下了冷静键。本卡补完，让用户在最不冷静的时刻也有后悔药。

---

## 背景

`docs/ROADMAP.md` Phase 1 候选第 4 项落地。本卡是 Phase 1 三张串行卡（W1/W2/W3）中的第二张。

**现状摘录**（实现工可读代码确认）：

- `frontend/streamlit_app/pages/tab_settings.py` 191-214：解除绑定 expander 有「进入冻结期」/「双方同意立即销毁」两个按钮，**点击立即生效**，无二次确认
- 同上 216-239：冻结期 settings UI 仅展示到期时间 + 数据导出，**没有"撤回"入口**
- `backend/application/couples/uncoupling.py`：`start_uncouple(user_id)` / `confirm_uncouple(user_id)` / `is_frozen(user_id)` 已就绪；**缺少 `cancel_uncouple`**
- `backend/domain/models/couple.py` 字段就绪：`couple_status` / `uncouple_initiated_by` / `uncouple_initiated_at` / `freeze_ends_at` / `both_agreed_uncouple`
- `backend/application/maintenance/ticking.py` 检测 `freeze_ends_at` 触发自动销毁，已就绪
- 已有二次确认模式可以参考：`render_comments` 中评论删除的 `pending_delete_*` 状态机

## 要做的改动

1. **进入冻结期 · 二次确认**：「进入冻结期」按钮改为两步确认（参考评论删除的 `pending_*` 状态机）。确认面板文案克制——不要"确定吗？" 这种工程感，也不要威吓口吻。给用户最后一次冷静的机会
2. **撤回冻结**（**核心新功能**）：新增 application 层 `cancel_uncouple(user_id)`——任一方在冻结期内可调用，行为：`couple_status` 改回 `active`、清除 `uncouple_initiated_by` / `uncouple_initiated_at` / `freeze_ends_at` / `both_agreed_uncouple`。同步加 `ensure_can_cancel_uncouple` 校验（非冻结期 / 无 couple 时抛 `CoupleError`）+ pytest 覆盖、`backend/application/couples/__init__.py` 导出、L2 `docs/api/app_couple.md` 同步
3. **撤回入口 UI**：冻结期「设置」内展示显眼的「撤回冻结」入口（任一方可点）；同样二次确认；撤回成功后 UI 反馈"已回到正常状态"，应用恢复正常交互
4. **双方端可见性 banner**：进入冻结期后，**发起方 + 接收方**都能在 Streamlit 顶部（或「我们」/「我的」tab 顶部）看到克制 banner：「你们处于冻结期，还有 N 天 · 任一方可撤回」。banner 上直接提供「撤回冻结」入口（二次确认）。banner 文案对发起方与接收方略有区分（"是你按下了冷静键" vs "对方按下了冷静键"），不要任何责备口吻
5. **双方同意立即销毁 · 二次确认**：当前一键即销毁全数据，过于轻易。改为两步确认。文案要明确告知"销毁后无法恢复"
6. **销毁瞬间的 UX 转场**：当前销毁后只 `st.error("已销毁全部数据")` + 清 session 跳回登录，太冷冰冰。改为温柔克制的告别页（短文案 + 数据已不可恢复声明 + 自动跳回登录），不再停留在 settings tab
7. **冻结期只读态文案一致性**：复查 `tab_us` / `tab_mine` / `tab_settings` 在 `couple_status == "frozen"` 时的所有"只读"提示文案，统一基调（克制、不威吓、不重复说"应用只读"四次）；自动隐藏所有写入 / 编辑 / 申请共享 / 追加 / 立即解锁动作（已有逻辑复查即可）
8. **L2 文档同步**：`docs/api/app_couple.md` 加 `cancel_uncouple` 完整签名 + `ensure_can_cancel_uncouple` 校验；`docs/api/frontend_streamlit.md` 同步 settings tab + 全局 banner 行为
9. **`CHANGELOG.md` `[Unreleased]`**：1-2 句总结用户可见变化

## 涉及文件

- `frontend/streamlit_app/components.py`（如果 banner 抽成共用 helper）
- `frontend/streamlit_app/pages/tab_settings.py`（确认流程、撤回入口、文案）
- `frontend/streamlit_app/pages/tab_us.py` + `pages/tab_mine.py` **或** `main.py`（banner 放置位置实现工自选，但必须双 tab 都可见）
- `backend/application/couples/uncoupling.py`（新增 `cancel_uncouple`）
- `backend/application/couples/policies.py`（新增 `ensure_can_cancel_uncouple`）
- `backend/application/couples/__init__.py`（导出）
- `backend/tests/`（`cancel_uncouple` 完整覆盖 + 边界 case）
- `docs/api/app_couple.md`
- `docs/api/frontend_streamlit.md`
- `CHANGELOG.md`

## 验收（用户可见行为）

- 点「进入冻结期」→ 二次确认面板出现 → 确认后才生效；取消则关闭面板，关系仍为 active
- 进入冻结期后**双方** Streamlit 顶部 banner 立刻出现："你们处于冻结期，还有 N 天 · 任一方可撤回"，发起方 / 接收方文案略有区分
- 任一方点 banner 或 settings 里的「撤回冻结」→ 二次确认 → 关系回到 active，所有已有数据完整保留，banner 消失
- 冻结期内 `tab_us` / `tab_mine` 没有任何写入 / 编辑 / 申请共享 / 追加 / 立即解锁动作；提示文案统一克制
- 点「双方同意立即销毁」→ 二次确认 → 确认后进入告别页（不留在 settings tab）→ 自动跳回登录
- `cancel_uncouple` 在非冻结期 / 无 couple 时调用抛 `CoupleError`，pytest 覆盖
- `docs/api/app_couple.md` 有 `cancel_uncouple` / `ensure_can_cancel_uncouple` 完整说明；`docs/api/frontend_streamlit.md` 同步 settings tab + banner 行为

## 不要做

- **不要修改"双方同意立即销毁"的协议本身**：当前是单方点击即触发，**这是 W2 范围外的更大设计变更**（真正双方握手协议）。本卡只在 UX 层加二次确认，不动 `confirm_uncouple` 的后端语义
- **不要修改 `ticking.py` 的自动销毁逻辑**——`cancel_uncouple` 只清理 `couple_status` / 冻结相关字段，自动销毁条件自然失效，无需改 ticking
- **不要触碰 `docs/STATUS.md`、`docs/DIRECTION.md`、`docs/ROADMAP.md`、`docs/E2EE.md`、`docs/PRD.md`、`CLAUDE.md`**——架构师独占
- 不要做新手引导、三视图信息架构重组（W3 范围）
- 不要做"账号删除"或其他销毁路径（本卡范围只在 couple 冻结期销毁）
- 不要引入第三方依赖 / 自定义 CSS / Streamlit components
- 不要在 banner 用威吓 / 情绪化文案（"你确定要分手吗？！"），保持产品克制基调

## 提交规约

- `pytest backend/tests/` 整库通过（含新增的 `cancel_uncouple` 覆盖）
- `ruff check .` 通过
- 自行启动 Streamlit 验收，**端口必须指定非默认值**（默认 8501 大概率被架构师本机占用），例如 `streamlit run main.py --server.port 8765`
- **必须用两个账号**（一个发起方 / 一个接收方）分别验收冻结流程全链路：进入 → banner 出现 → 撤回 → banner 消失 → 数据完整；以及进入 → 双方同意立即销毁 → 告别页
- commit message 形如 `ux(freeze): 冻结期销毁完整链路 · 关联 #25`，可拆多个 commit
