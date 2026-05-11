### `backend/application/maintenance/ticking.py` — 生命周期推进

负责自动状态推进，不直接处理 UI。

```python
def tick(db: dict) -> bool
```

- 在已加载的 `db` 对象上原地推进状态
- 若有变化返回 `True`
- 处理三类事情：
  1. `pending_unlock` 且 `unlock_at <= now` 时推进为 `shared`
  2. `frozen` 到期后自动调用 `destroy_couple_data()`
  3. 清理过期 `auth_tokens`

共享推进只读取 session 的 `unlock_at` 字段，不再根据 `upload_time` 或固定天数计算。

```python
def load_db_with_tick() -> dict
```

- 加载 DB
- 调用 `tick()`
- 若有变化则保存并重新加载一次
- UI 层应优先调用这个函数，而不是直接调用 `load_db()`
