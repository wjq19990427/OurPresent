# Task 5: pending_unlock session 流动性增强

**类型**：feature（让延时表达保留可调整空间）
**Branch**：`codex/task-5`
**前置任务**：**task-4 已合并**（依赖 `SessionRecord.unlock_at` 字段和 `request_unlock(session_id, unlock_at)` 签名）

## 背景

task-4 把 90 天硬编码改成了用户自选 `unlock_at`。但情感是流动的：一周前申请共享时觉得「再等一个月吧」，今天可能已经平静下来想立刻让对方看见；或者越想越觉得还要再多说几句、应该再缓一缓。本任务让 `pending_unlock` 状态下的 session 仍然保留调整空间，避免「申请共享」变成一次性不可挽回的操作。

## 目标

为 `visibility == "pending_unlock"` 的 session 提供四种动作（撤回已存在，需确认 UI 链路完整）：

1. **追加内容**：在原字段内容基础上向后追加，保留原始版本（区别于 task-4 之前已有的「覆盖式编辑」）
2. **立即解锁**：跳过倒计时，session 立即进入 `shared`
3. **修改 unlock_at**：把目标时间提前或推后
4. **撤回**：（已有 `revoke_unlock`，本任务确认 UI 入口可达）

## 改动范围

**许动**：

- `backend/application/sessions/sharing.py`（新增「立即解锁」「修改 unlock_at」两个用例函数）
- `backend/application/sessions/editing.py`（新增「追加内容」用例函数；不修改 `update_session_fields` 现有签名）
- `frontend/streamlit_app/`（pending_unlock 状态下的详情区暴露四个动作；其中「修改 unlock_at」与「立即解锁」必须有二次确认）
- `backend/tests/`（覆盖三个新动作的成功路径与状态约束）

**不许动**：

- `request_unlock` 签名（task-4 已定型）
- `tick()` 推进逻辑（task-4 已改）
- `update_session_fields` / `move_to_final` 等 status 流程相关函数
- `private` / `shared` / `status=pending` / `status=final` 状态下的任何已有行为
- `couples` / `auth` / `tokens` / `destruction` / `maintenance`

## 接口约定

新增三个 application 层函数（命名可微调，语义不可变）：

```python
def unlock_now(session_id: str) -> None
```

- 前置条件：`visibility == "pending_unlock"`，否则抛错或静默 no-op（实现工自决，但要在测试中固化）
- 行为：`visibility → "shared"`，写入 `shared_at = now`，`unlock_at` 同步对齐到 `now`（避免「shared 但 unlock_at 是未来」的不一致）

```python
def reschedule_unlock(session_id: str, new_unlock_at: str) -> None
```

- 前置条件：`visibility == "pending_unlock"`
- 行为：仅更新 `session.unlock_at = new_unlock_at`；`visibility` 保持 `pending_unlock`，`unlock_requested_at` 不变
- 若 `new_unlock_at <= now`：等同 `unlock_now`，避免出现「unlock_at 是过去时间但状态仍是 pending_unlock」的死状态（下次 tick 自然会推，但本函数应即时纠正）

```python
def append_to_session(session_id: str, field: str, text: str) -> None
```

- 前置条件：`visibility == "pending_unlock"`
- 允许追加的字段集合限定为 `FIELD_SCHEMA` 中的文本类字段（`description` / `feeling` / `reason`）；其他字段拒绝
- 行为：把 `text` 拼接到指定字段原值之后；拼接形式由实现工自决，但**必须能在 UI 中区分原文与追加段**（例如带「[追加于 时间]」分隔标记），让伴侣解锁时看到的是一条带追加痕迹的完整记录，而非覆盖
- 不写入 `edit_history`（那是 final 阶段的字段 diff 记录，与「追加」语义无关）

## UI 二次确认约束

「修改 unlock_at」与「立即解锁」两个动作必须有二次确认弹窗或勾选框，明确告知用户「这会改变伴侣看见这条记录的时间」。这条不是体验润色，是产品约束：防止时间锁因为操作太轻量而形同虚设。

「追加内容」与「撤回」不强制二次确认。

## 验收行为（用户视角）

`uv run streamlit run main.py` 跑通：

- 申请共享（1 个月后）→ 进入 `pending_unlock` → 在详情区追加一段 feeling → DB 中 `feeling` 字段含原文 + 追加段，伴侣此时仍看不到
- 同一条 session 上点「立即解锁」→ 二次确认 → 伴侣立刻在情侣空间看到完整内容（含追加段）
- 另起一条 session：申请共享（1 周后）→ 点「修改时间」→ 改为 1 天后 → 二次确认 → `unlock_at` 已更新；tick 满 1 天后该 session 进入 shared
- 修改时间时把目标时间设为过去 → 自动等同立即解锁，不出现「pending_unlock 但 unlock_at 已过期」的死状态
- 撤回功能 UI 入口可达且行为正确（清空 `unlock_at` 与 `unlock_requested_at`，回到 `private`）
- `visibility == "private"` 或 `"shared"` 的 session 上不暴露这四个动作的入口

自动化检查：

- `uv run pytest` 全绿，覆盖：追加保留原文、立即解锁的状态一致性、reschedule 改未来时间、reschedule 改过去时间等同立即、非 pending_unlock 状态下三个新函数被拒绝
- `uv run ruff check .` 无错

## 已知陷阱

- 追加内容会改写 session 字段，确保不会触发 final 阶段的 `edit_history` 副作用（这是 task-4 之前 `update_session_fields` 的已有行为）
- 「立即解锁」要走和 task-4 中「立即档位」相同的路径——保证 `unlock_at == shared_at` 的一致性，便于事后审计
- 追加段的格式如果未来要被 RAG/AI 解析，分隔标记需要稳定可识别（但本任务不引入 AI，分隔标记格式由实现工自决即可）

## 必读契约

- `docs/api/app_sessions.md`（sharing 和 editing 当前签名，task-4 合并后已更新）
- `docs/api/domain_models.md`（SessionRecord 字段，task-4 合并后已含 `unlock_at`）
- `docs/api/frontend_streamlit.md`（详情区当前结构）

## 文档同步

以上 3 份 L2 契约均需同步新增的三个函数与 UI 入口描述。`docs/STATUS.md` 与 `CHANGELOG.md` 不动（架构师维护）。
