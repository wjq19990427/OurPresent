### `main.py` — 应用入口

```python
def _init_state() -> None
```

- 初始化 `st.session_state` 默认键：
  - `user`
  - `upload_key`
  - `pending_selected`
  - `archived_selected`
  - `shared_selected`
  - `auth_tab`
- 若 URL 中存在 `token`，尝试自动恢复登录

```python
def render_auth_page() -> None
```

- 渲染登录 / 注册页
- 登录成功后：
  - 调用 `create_auth_token()`
  - 将 token 写入 `st.query_params`
  - 保存当前 `User` 到 `session_state`

```python
def main() -> None
```

- 应用主入口
- 调用顺序大致为：
  1. `ensure_dirs()`
  2. `_init_state()`
  3. 未登录则显示 `render_auth_page()`
  4. 已登录则调用 `load_db_with_tick()`
  5. 渲染五个主 Tab

当前 `st.session_state` 关键键：

| 键名 | 类型 | 说明 |
|------|------|------|
| `user` | `User | None` | 当前登录用户 |
| `upload_key` | `int` | 上传控件重置计数器 |
| `pending_selected` | `str | None` | 灵感墙当前选中的 `session_id` |
| `archived_selected` | `str | None` | 已归档当前选中的 `session_id` |
| `shared_selected` | `str | None` | 情侣空间当前选中的 `session_id` |
| `auth_tab` | `str` | 登录页内部标签状态 |

---

## 当前层次约束

```text
frontend/streamlit_app
  -> backend/application
  -> backend/config
  -> backend/infrastructure（查询型依赖）

backend/application
  -> backend/infrastructure
  -> backend/domain
  -> backend/config

backend/infrastructure
  -> backend/domain
  -> backend/config
```
