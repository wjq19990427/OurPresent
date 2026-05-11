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

#### 显示辅助

```python
def _session_thumb(session: SessionRecord)
```

- 返回 `(缩略图, 文本标签)`
- 行为：
  - 图片：返回 PIL Image
  - 视频：调用 `video_thumbnail()`
  - 文本：返回文本预览
  - 无文件：回退到 `description` 预览

```python
def _days_until_unlock(session: SessionRecord) -> int
```

- 基于 `unlock_at` 计算距离开放还剩几天

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

- 返回可见性标签：
  - `🔒 私密`
  - `⏳ 待解锁（还需 N 天）`
  - `✅ 已共享`

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

参数说明：

| 参数 | 说明 |
|------|------|
| `prefix` | widget key 前缀，需保证同页唯一 |
| `defaults` | 默认 session，常用于编辑态回填 |
| `skip_keys` | 跳过渲染的字段集合 |

#### 评论区

```python
def render_comments(session: SessionRecord) -> None
```

- 渲染评论列表
- 提供删除按钮和新增评论输入区
- 发送评论时调用 `add_comment()`

#### Session 卡片

```python
def render_card(col, session: SessionRecord, state_key: str) -> None
```

- 在指定列容器中渲染 session 卡片
- 展示缩略图、文件数、评论数、隐私状态、完整度
- 点击按钮后把 `session_id` 写入 `st.session_state[state_key]`

#### Session 详情区

```python
def render_detail(session: SessionRecord, mode: str, read_only: bool = False) -> None
```

- 渲染详情、预览、编辑历史、编辑表单和评论区

参数说明：

| 参数 | 说明 |
|------|------|
| `mode` | `"pending"` 或 `"final"` |
| `read_only` | 冻结期或查看对方共享记录时为 `True` |

行为说明：

- `read_only=False` 时可编辑字段
- `mode="pending"` 时支持“完成并归档”
- 自己的记录可申请共享或撤回共享
- 申请共享时默认选中“1 周后”，可选择“立即”、预设天数或日历自定义日期；最终调用 `request_unlock(session_id, unlock_at)`
- 自己的 `visibility == "pending_unlock"` 记录在详情区暴露四个动作：
  - 追加内容：可向 `description` / `feeling` / `reason` 追加文本，调用 `append_to_session()`
  - 修改开放时间：可选择新的预设或自定义日期，勾选确认后调用 `reschedule_unlock()`
  - 立即解锁：勾选确认后调用 `unlock_now()`
  - 撤回共享申请：调用 `revoke_unlock()`
- “修改开放时间”和“立即解锁”必须通过确认勾选，明确提示会改变伴侣看见记录的时间
- `visibility == "private"` 或 `"shared"` 的记录不展示 pending 解锁调整动作
- 纯文字记录的 `description` 不可手动修改

---

### `frontend/streamlit_app/pages/` — 页面模块

每个页面函数负责组织 UI 交互，不承载核心业务规则。

```python
def render_upload_tab() -> None
```

- Tab 1「🗂️ 记录舱」
- 支持上传文件或粘贴文字
- 可选择“完成并归档”或“暂存到待处理”
- 调用：
  - `save_session_final()`
  - `save_session_pending()`

```python
def render_pending_tab(db: dict) -> None
```

- Tab 2「🖼️ 灵感墙」
- 通过 `sessions_repo` 读取当前用户所有 `status == "pending"` 的 `SessionRecord`
- 点击卡片后调用 `render_detail(..., mode="pending")`

```python
def render_archived_tab(db: dict) -> None
```

- Tab 3「📚 已归档」
- 通过 `sessions_repo` 读取当前用户所有 `status == "final"` 的 `SessionRecord`
- 点击卡片后调用 `render_detail(..., mode="final")`

```python
def render_shared_tab(db: dict) -> None
```

- Tab 4「💌 情侣空间」
- 仅展示伴侣共享给自己的 `visibility == "shared"` 的 `SessionRecord`
- 使用 `can_view_session()` 做二次权限校验
- 全部只读查看

```python
def render_account_tab(db: dict) -> None
```

- Tab 5「⚙️ 账户」
- 包含：
  - 当前账户信息
  - 收到的绑定请求
  - 情侣关系面板
  - 分手协议入口
  - 冻结期导出入口

情侣状态对应 UI：

| `couple_status` | 展示内容 |
|-----------------|----------|
| 无关系 | 输入伴侣 ID 并发送绑定请求 |
| `pending_bind` | 发送方显示等待提示，接收方显示接受/拒绝引导 |
| `active` | 展示已绑定信息和解绑入口 |
| `frozen` | 展示冻结提示和导出入口 |
