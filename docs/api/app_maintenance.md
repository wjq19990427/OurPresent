### `backend/application/maintenance/ticking.py` — 生命周期推进

负责自动状态推进，不直接处理 UI。

```python
def tick(db: dict) -> bool
```

- 在已加载的 `db` 对象上原地推进状态
- 若有变化返回 `True`
- 处理四类事情：
  1. `pending_unlock` 且 `unlock_at <= now` 时推进为 `shared`
  2. `frozen` 到期后自动调用 `destroy_couple_data()`
  3. 清理过期 `auth_tokens`
  4. 对满足周报调度条件的 active couple 调用 `generate_weekly_report()`

共享推进只读取 session 的 `unlock_at` 字段，不再根据 `upload_time` 或固定天数计算。

周报触发在 session 推进、冻结期销毁、token 清理之后执行。单个 couple 生成异常会被记录并跳过，不影响同一轮 tick 中其他 couple；生成返回的 report 会同步回传入的 `db["reports"]`，由外层 `load_db_with_tick()` 统一保存。失败报告允许下一次 tick 重试一次；若重试仍为 `failed`，则跳过直到 `previous_window_end + weekly_report_interval_days <= now` 进入下一周期。

```python
def load_db_with_tick() -> dict
```

- 加载 DB
- 调用 `tick()`
- 若有变化则保存并重新加载一次
- UI 层应优先调用这个函数，而不是直接调用 `load_db()`
