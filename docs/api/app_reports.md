### `backend/application/reports/*` — 情感周报

本 L2 契约记录情感周报的数据底座、纯指标计算、查询用例与服务启用策略。周报生成、LLM 接入、调度与真实 UI 渲染将在 task-9 及后续任务中补齐。

---

### `backend/domain/models/report.py` — 周报模型

```python
class Report:
    report_id: str
    couple_id: str
    window_start: str
    window_end: str
    generated_at: str
    model_version: str
    footprint: dict
    weather: dict
    resonance: list[dict]
    suspense: list[dict]
    status: str
    source_session_ids: list[str]
```

- `report_id` 命名规则为 `rpt_YYYYMMDD_<couple_id>`
- `window_start` / `window_end` / `generated_at` 使用 `%Y-%m-%d %H:%M:%S`
- `model_version` 由生成用例写入；当前数据层允许为空串
- `status` 取值约定为 `ready` / `failed` / `sparse`
- `footprint` / `weather` / `resonance` / `suspense` 分别保存周报四个模块的结构化数据
- `source_session_ids` 保存生成报告使用过的 session id，供审计与排障
- `from_dict()` / `to_dict()` 用于 repository 持久化边界

---

### `backend/infrastructure/database/reports_repo.py` — 周报仓储

```python
def create_report(report: Report) -> None
```

- 新增一份 report
- 不负责生成 `report_id`，调用方需保证唯一

```python
def get_report(report_id: str) -> Report | None
```

- 按 `report_id` 读取 report
- 未找到返回 `None`

```python
def list_reports_for_couple(couple_id: str) -> list[Report]
```

- 返回指定 couple 的全部 report
- 按 `generated_at` 倒序排列

```python
def update_report(report: Report) -> None
```

- 按 `report_id` 替换已有 report
- 未找到时不新增
- 预留给后续失败重试覆盖写入

```python
def delete_reports_for_couple(couple_id: str) -> int
```

- 删除指定 couple 的全部 reports
- 返回删除条数
- `destroy_couple_data()` 会在同一销毁链路中清理该 couple 的 reports

---

### `backend/application/reports/metrics.py` — 周报结构化指标

```python
def compute_footprint(
    sessions: list[SessionRecord],
    window: tuple[datetime, datetime],
) -> dict
```

- 输入为指定 couple 在窗口内的 shared sessions 与窗口边界
- 输出字段：
  - `total`：窗口内 session 数
  - `by_kind`：按 `photo` / `video` / `text` 计数
  - `active_days`：基于 `shared_at` 的活跃日期数
  - `comment_count`：评论总数
  - `by_author`：按 `user_id` 计数
- `kind` 由 `source_type` 与附件扩展名推导；纯文本 source 或文本附件为 `text`，图片扩展名为 `photo`，视频扩展名为 `video`
- 不写库、不调用外部服务

```python
def compute_suspense(couple_id: str, now: datetime) -> list[dict]
```

- 返回指定 couple 当前所有 `visibility == "pending_unlock"` 的 session 元数据
- 按 `unlock_at` 升序排列
- 输出字段：
  - `session_id`
  - `unlock_at`
  - `days_remaining`
  - `kind`
- 只返回元数据，不读取或抽取 private / pending_unlock 正文内容

---

### `backend/application/reports/query.py` — 周报查询用例

```python
def list_reports(couple_id: str) -> list[Report]
```

- 委托 `reports_repo.list_reports_for_couple()`
- 返回指定 couple 的全部 reports，按 `generated_at` 倒序
- 包含 `failed`，供排障使用

```python
def get_latest_ready_report(couple_id: str) -> Report | None
```

- 返回最新可见 report
- 可见态为 `status in {"ready", "sparse"}`
- `sparse` 算可见态，`failed` 不作为 UI 展示候选

```python
def get_report(report_id: str) -> Report | None
```

- 委托 `reports_repo.get_report()`
- 未找到返回 `None`

---

### `backend/application/reports/policies.py` — 周报服务策略

```python
def service_active_for_couple(couple_id: str) -> bool
```

- 仅当 couple 存在、状态为 `active`，且双方 `User.weekly_report_enabled` 都为 `True` 时返回 `True`
- 任一方不存在、未绑定、关系非 active 或未开启时返回 `False`

```python
def partner_enabled_status(user_id: str) -> Literal[
    "both",
    "only_self",
    "only_partner",
    "neither",
]
```

- 从当前 user 视角描述双方周报开关组合
- 未绑定或非 active 关系下，对方视为未开启
  - `both`：双方都开启
  - `only_self`：仅当前用户开启
  - `only_partner`：仅伴侣开启
  - `neither`：双方都未开启
