### `frontend/streamlit_app/components.py` — Streamlit UI 组件

所有函数都依赖已登录的 `st.session_state["user"]`。

#### 会话状态工具

```python
def _current_user() -> Optional[User]
```

- 返回 `st.session_state["user"]`

```python
def _uid() -> str
```

- 返回当前用户 `user_id`

```python
def _is_frozen() -> bool
```

- 返回当前用户是否处于冻结期

```python
def _couple() -> Optional[Couple]
```

- 返回当前用户对应的情侣关系对象

```python
def _partner_id() -> Optional[str]
```

- 在 `active` 关系下返回伴侣 `user_id`
- 未绑定或非激活状态返回 `None`

```python
def render_frozen_status_banner(*, scope: str) -> None
```

- 在当前用户处于 `frozen` 关系时渲染顶部 / 设置页共用 banner
- 同时承载冻结期撤回协议的三态 UI：
  - 无 pending 请求：展示「撤回冻结」入口，点击后二次确认并调用 `request_cancel_uncouple()`
  - 当前用户是请求发起方：展示「已发出撤回请求」状态与「撤回我的请求」入口，点击后二次确认并调用 `withdraw_cancel_request()`
  - 当前用户是请求接收方：展示「同意撤回 / 拒绝撤回」两个入口，点击后二次确认并分别调用 `confirm_cancel_uncouple()` / `reject_cancel_uncouple()`
- banner 文案区分发起冻结的一方与接收方，但都显示剩余冻结天数与自动销毁说明

#### 显示辅助

```python
def _session_thumb(session: SessionRecord)
```

- 返回 `(缩略图, 文本标签)`
- 行为：
  - 图片：返回 PIL Image
  - 视频：返回文件名提示；实际播放由卡片预览渲染负责
  - 文本：返回文本预览
  - 无文件：回退到 `description` 预览

```python
def _days_until_unlock(session: SessionRecord) -> int
```

- 基于 `unlock_at` 计算距离开放还剩几天

```python
def _time_until_unlock_text(session: SessionRecord) -> str
```

- 基于 `unlock_at` 返回克制的等待文案：
  - 已到时间：`即将开放`
  - 天级：`还要 N 天`
  - 小时级：`还要 N 小时`
  - 分钟级：`还要 N 分钟`
  - 缺少时间：`开放时间待定`

```python
def _is_recently_shared(session: SessionRecord) -> bool
```

- 基于 `shared_at` 判断记录是否在 24 小时内解锁

```python
def _unlock_at_for_choice(
    choice: str,
    custom_date: date | None = None,
    anchor: datetime | None = None,
) -> str
```

- 将申请共享 UI 的档位转换为 `unlock_at` 字符串
- 支持：立即、1 天后、3 天后、1 周后、1 个月后、90 天后、自定义日期
- `anchor` 默认为按钮按下时的当前时间

```python
def _visibility_badge(session: SessionRecord) -> str
```

- 返回详情区可见性标签：
  - `🔒 私密`
  - `等待开放（还要 N 天/小时/分钟）`
  - `✅ 已共享`

```python
def _status_badge(session: SessionRecord) -> str
```

- 返回卡片状态标签：
  - `status == "pending"`：`[草稿]`
  - `status == "final" and visibility == "private"`：`[仅自己]`
  - `status == "final" and visibility == "pending_unlock"`：`[等待开放 · 还要 N 天/小时/分钟]`
  - `status == "final" and visibility == "shared"`：`[已分享]`

```python
def _looks_like_date(value: str) -> bool
```

- 判断字符串是否符合 `YYYY-MM-DD` 格式

#### 表单渲染

```python
def render_field_inputs(
    prefix: str,
    defaults: Optional[SessionRecord] = None,
    skip_keys: Optional[set] = None,
) -> dict
```

- 遍历 `FIELD_SCHEMA` 生成输入控件
- 通常在 `st.form()` 中调用
- 返回值是字段值字典
- `prefix == "upload"` 时按首次填写旅程排序：`description → feeling → reason → content_time`
- 其他前缀保持 `FIELD_SCHEMA` 原顺序，用于编辑态稳定回填

参数说明：

| 参数 | 说明 |
|------|------|
| `prefix` | widget key 前缀，需保证同页唯一 |
| `defaults` | 默认 session，常用于编辑态回填 |
| `skip_keys` | 跳过渲染的字段集合 |

#### 评论区

```python
def render_comments(session: SessionRecord, *, key_scope: str = "comments") -> None
```

- 渲染评论列表
- 仅对当前用户自己写的评论提供删除按钮，并在删除前显示确认警示
- `key_scope` 用于给评论区内部 widgets 做 key 作用域隔离，避免同一条评论在不同 tab / 详情区重复渲染时发生 key 冲突
- 发送评论时调用 `add_comment()`

#### Session 卡片

```python
def render_card(
    col,
    session: SessionRecord,
    state_key: str,
    author_name: str | None = None,
    *,
    author_relation: str | None = None,
    show_completion: bool = True,
    show_recently_shared: bool = False,
    button_label: str | None = None,
    show_status_badge: bool = True,
    show_description: bool = False,
) -> None
```

- 在指定列容器中渲染 session 卡片
- 展示可选作者徽章、缩略图、文件数、评论数、可选状态徽章、可选描述、完整度
- `author_relation` 用于在「我们」tab 明确展示 `我的记录` / `对方的记录`，保证手机宽度下仍能一眼区分归属
- `show_completion=False` 时隐藏“信息完整 / 待补充”提示，用于阅读态时间线
- `show_recently_shared=True` 时，对 `shared_at` 距当前时间 24 小时内的记录显示 `新近解锁`
- `button_label` 用于阅读态覆盖按钮文案；「我的」tab 默认仍按作者显示 `查看/编辑`
- `show_status_badge=False` 时隐藏状态徽章；`show_description=True` 时在计数信息下方直接展示 `description`
- 点击按钮后切换 `st.session_state[state_key]`：当前卡片已展开则收起，否则展开当前卡片

#### Session 详情区

```python
def render_detail(
    session: SessionRecord,
    mode: str,
    read_only: bool = False,
    *,
    selected_state_key: str,
    show_comments: bool | None = None,
    show_file_preview: bool = True,
) -> None
```

- 渲染详情、预览、编辑历史、编辑表单和评论区

参数说明：

| 参数 | 说明 |
|------|------|
| `mode` | `"pending"` 或 `"final"` |
| `read_only` | 冻结期或查看共享记录时为 `True` |
| `selected_state_key` | 取消或归档后需要清空的选中状态 key（关键字参数，必填） |
| `show_comments` | `None` 时按 visibility 自动判断；显式传入时覆盖评论区展示 |
| `show_file_preview` | `False` 时隐藏详情区的 `📁 文件预览` 展开面板 |

行为说明：

- `read_only=False` 时可编辑字段
- `mode="pending"` 时支持“完成”
- 自己的记录可申请共享或撤回共享
- 申请共享时默认选中“1 个月后”，并提示默认等待一个月的产品理由；仍可选择“立即”、预设天数或日历自定义日期；最终调用 `request_unlock(session_id, unlock_at)`
- 自己的 `visibility == "pending_unlock"` 记录在详情区暴露四个动作：
  - 追加内容：可向 `description` / `feeling` / `reason` 追加文本，调用 `append_to_session()`
  - 修改开放时间：可选择新的预设或自定义日期，勾选确认后调用 `reschedule_unlock()`
  - 立即解锁：勾选确认后调用 `unlock_now()`
  - 撤回共享申请：调用 `revoke_unlock()`
- “修改开放时间”和“立即解锁”必须通过确认勾选，明确提示会改变伴侣看见记录的时间
- `visibility == "private"` 或 `"shared"` 的记录不展示 pending 解锁调整动作
- 纯文字记录的 `description` 不可手动修改
- `read_only=True` 时不展示字段编辑、共享申请、撤回、追加、修改时间、立即解锁等自身记录操作
- 评论区默认可见规则：
  - `visibility == "private"`：仅作者本人可见可写
  - `visibility == "pending_unlock"`：完全隐藏
  - `visibility == "shared"`：双方可见可写

#### 情感周报渲染

```python
def render_weekly_report(report: Report) -> None
```

- 渲染一份可见周报
- `ready` 渲染顺序为 footprint → weather → resonance → suspense
- `sparse` 仅渲染 footprint，并显示温和说明「这周共享记录较少，留些空白也好。」
- suspense 只展示 kind 图标、剩余天数与 unlock 时间，不展示 session 文本字段

```python
def render_report_history(reports: list[Report]) -> None
```

- 渲染周报历史列表
- 按 `generated_at` 倒序
- 过滤 `status == "failed"`，不向普通 UI 暴露失败项
- 列表项展示 `window_start ~ window_end` 与状态徽章，点击展开后调用 `render_weekly_report()`

---

### `frontend/streamlit_app/pages/` — 页面模块

每个页面函数负责组织 UI 交互，不承载核心业务规则。

```python
def render_us_tab(db: dict) -> None
```

- Tab 1「🏠 我们」，登录后默认落地页
- 当关系处于 `frozen` 时，登录后的页面顶部会显示共用冻结期 banner
- 未绑定伴侣时提示去「设置」绑定
- pending bind 时提示绑定确认后出现共享记录
- active / frozen 关系下，在 shared 时间线之上显示「📊 周报」区块
- 周报区状态矩阵：
  - 双方都未开启：显示「一起开启情感周报，每周看到我们的足迹」并引导去「设置」
  - 仅当前用户开启：显示「⌛ 等待对方一同开启」，并提示对方在「设置」里的位置
  - 仅伴侣开启：显示「对方已开启周报，要不要一起？」并引导去「设置」
  - 双方都开启且无任何 report：显示第一周共享记录邀请文案，不出现「立即生成」字样
  - 双方都开启且最新 `status == "ready"`：渲染完整周报
  - 双方都开启且最新 `status == "sparse"`：仅渲染 footprint 与温和提示
  - 双方都开启且最新 `status == "failed"`：显示「上一次生成遇到了一些波折，会在下次自动重试」，不展示报告内容或错误细节
  - 冻结期：显示冻结说明，不展示手动生成入口；已生成的 ready/sparse 历史仍可读
- 双方都开启服务且关系 active 时显示临时测试按钮「🧪 立即生成周报（测试）」并调用 `generate_weekly_report(couple_id)`；该入口将在 cron 稳定后删除
- 读取当前 couple 下所有 `visibility == "shared"` 的 `SessionRecord`
- 同时读取伴侣的 `visibility == "pending_unlock"` 记录并在共享时间线上方展示预告区块
- 预告区块只展示“有记录正在路上”和开放时间，不展示作者写了什么、文件类型、描述、感受、原因或 session 内容字段
- 过滤条件：
  - `session.couple_id == couple.couple_id`
  - `session.visibility == "shared"`
  - `can_view_session(session, current_user_id)` 二次权限校验
- 按 `shared_at` 倒序
- 视觉规则：
  - 当前用户自己的记录靠右
  - 伴侣的记录靠左
  - 卡片顶部展示 `我的记录 / 对方的记录` 与作者用户名，移动端分栏折叠时仍保留归属信号
  - 共享时间线隐藏“信息完整 / 待补充”写作者元信息
  - `shared_at` 距当前时间 24 小时内的记录显示 `新近解锁`
  - 共享时间线不展示 `[已分享]` 状态徽章；`description` 直接显示在计数信息下方
  - 卡片按钮统一显示 `评论`
- 点击 `评论` 后，仅在所属卡片下方内嵌展开评论区；再次点击同一按钮会收起
- 「我们」tab 不再额外渲染 `xxx 的记录` 标题、文件预览或只读字段详情，避免与卡片预览重复
- 不展示编辑字段、申请共享、撤回、追加、修改时间、立即解锁等自身记录操作

```python
def render_mine_tab(db: dict) -> None
```

- Tab 2「📝 我的」
- 当关系处于 `frozen` 时，登录后的页面顶部会显示共用冻结期 banner
- 顶部提供「✍️ 写新记录」入口
- 当前用户没有任何记录时，入口默认展开并展示首条记录引导；已有记录后保持折叠
- 写新记录入口支持上传文件或粘贴文字
- 可选择“完成”或“存为草稿”
- 创建记录时调用：
  - `save_session_final()`
  - `save_session_pending()`
- 时间线读取当前用户未共享的 `SessionRecord`
- 过滤条件：`session.user_id == current_user_id and session.visibility != "shared"`
- 按 `upload_time` 倒序
- 每条卡片展示 `_status_badge()` 的 4 种状态标签
- 卡片外层直接渲染首个附件预览；若首个附件是视频，则在卡片中直接可播放
- 点击 `查看/编辑` 后，详情区紧贴所属卡片内嵌展开；再次点击同一按钮会收起，不在页面底部集中展开
- 已进入 `shared` 的记录不再出现在「我的」，避免与「我们」重复
- 详情区承载当前用户自己的所有记录操作：
  - 草稿：继续编辑字段、完成
  - 仅自己：编辑字段、申请共享
  - 等待开放中：追加内容、修改时间、立即解锁、撤回共享申请
- `couple_status == "frozen"` 时不展示新建入口，详情区继续以 `read_only=True` 隐藏编辑、申请共享、撤回、追加、修改时间、立即解锁等写操作
- 「我的」tab 不展示评论区；评论互动仅保留在「我们」tab
- 「我的」tab 不展示详情区的 `📁 文件预览`；附件预览统一放在卡片外层

```python
def render_settings_tab(db: dict) -> None
```

- Tab 3「⚙️ 设置」
- 包含：
  - 当前用户资料
  - 情感周报服务
  - 收到的绑定请求
  - 伴侣绑定面板
  - 解除绑定入口
  - 冻结期导出入口
- 「情感周报服务」section：
  - 显示当前用户 `weekly_report_enabled` 开关，切换立即持久化到 `User`
  - 开关旁说明：周报基于已共享记录生成，不读私密内容
  - 未绑定伴侣时 section 仍显示，开关只影响个人偏好，并提示新绑定关系的频率从默认 7 天 / 每周开始
  - pending bind 时提示绑定确认后双方开启即可生效
  - active 关系下展示对方开启状态
  - 当 `service_active_for_couple(couple_id)` 为 `True` 时显示频率选择，选项文案为 `7 天 / 每周`、`14 天 / 每两周`、`30 天 / 每月`，改动立即持久化到 `Couple.weekly_report_interval_days`
  - active / frozen 关系下展示「查看周报历史」入口，调用 `list_reports(couple_id)` 后由 `render_report_history()` 过滤 failed 并倒序展示
  - frozen 关系下展示冻结说明，开关只读，历史报告可读且不会生成新报告
- active 关系下，「进入冻结期」与「双方同意立即销毁」都采用两步确认状态机；前者确认后调用 `start_uncouple()`，后者确认后调用 `confirm_uncouple()`
- `confirm_uncouple()` 成功后不再停留在设置页，而是切到告别页短暂停留，再自动回到登录页
- frozen 关系下，settings 内部也复用 `render_frozen_status_banner()`，让用户能在设置页看到撤回冻结的三态入口与结果反馈
- 周报 UI 文案基调：
  - 保持温和、不评判、不指责任一方
  - 不使用「你应该」「你需要」「建议你」等祈使句
  - failed 只展示自动重试说明，不暴露错误细节

情侣状态对应 UI：

| `couple_status` | 展示内容 |
|-----------------|----------|
| 无关系 | 输入伴侣 ID 并发送绑定请求 |
| `pending_bind` | 发送方显示等待提示，接收方显示接受/拒绝引导 |
| `active` | 展示已绑定信息、二次确认后的「进入冻结期」与二次确认后的「双方同意立即销毁」入口 |
| `frozen` | 展示冻结 banner、撤回冻结三态入口与导出入口 |
