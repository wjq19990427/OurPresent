### `backend/application/reports/*` — 情感周报

本 L2 契约记录情感周报的数据底座、纯指标计算、查询用例、服务启用策略与手动生成 pipeline。

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
- 输入 session 必须包含可解析的 `shared_at`；缺失或无法解析时抛出 `ValueError`，表示调用方违反 footprint 输入契约
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

---

### `backend/application/reports/errors.py` — 周报异常

```python
class ReportGenerationError(RuntimeError)
```

- 生成入口在业务前置条件不满足时抛出
- 当前触发条件：couple 不存在，或 `service_active_for_couple(couple_id)` 为 False
- LLM 失败、guard 失败不抛该异常，而是持久化 `status="failed"` report

---

### `backend/application/reports/scheduling.py` — 周报调度判定

```python
def previous_report_window_end(couple_id: str, db: dict) -> datetime | None
```

- 在传入的整库 `db` 中查找该 couple 最新 report
- “最新”按 `window_end` 优先、`generated_at` 次序比较
- 返回最新 report 的 `window_end`；无 report 或时间无法解析时返回 `None`
- 不写库、不调用外部服务

```python
def should_generate_for_couple(couple: Couple, db: dict, now: datetime) -> bool
```

- 纯判定函数，只读取入参，不写库、不调用外部服务
- 返回 `True` 的条件：
  - `couple.couple_status == "active"`
  - 双方 `User.weekly_report_enabled` 都为 `True`
  - 上次 report 为 `failed` 且对应 retry 标记未消耗，允许下一次 tick 重试一次
  - 或 `now >= previous_window_end + Couple.weekly_report_interval_days`
  - 首次无 report 时，使用 `Couple.created_at` 作为稳定锚点；当前模型没有双方开启时间字段，因此服务开关仍作为前置条件，但不改变首次锚点
- tick 将进程内 retry 标记通过 `db["_weekly_report_retry_consumed"]` 提供给该纯函数；标记不属于持久化 L2 数据模型
- `frozen` / `dissolved` / `pending_bind` 或任一方关闭服务时始终返回 `False`

---

### `backend/application/reports/semantic.py` — 语义抽取

```python
def extract_semantic(sessions: list[SessionRecord], couple: Couple) -> tuple[dict, list[dict]]
```

- 输入为窗口内 shared sessions
- `couple` 用于将 resonance 候选严格对齐到 `Couple.user_a` / `Couple.user_b`
- 传给 LLM 的字段白名单严格限定为 `description` / `feeling` / `content_time` / `user_id`
- 不传 `session_id`、`files`、文件路径、`couple_id`
- 调用 `llm_client.extract_emotions()`、`llm_client.compose_weather_narrative()`、`llm_client.extract_resonance()`
- 返回：
  - `weather`: `{ "tags": list[dict], "narrative": str }`
  - `resonance`: `[{ "day", "topic", "user_a_excerpt", "user_b_excerpt" }]`，其中 `user_a_excerpt` / `user_b_excerpt` 分别对应 `Couple.user_a` / `Couple.user_b`
- resonance 按日期配对只使用可解析时间或合法 `YYYY-MM-DD` 的 `content_time` fallback；无有效日期的 session 不参与配对
- `weather.narrative` 截断到 80 字符；resonance excerpt 截断到 8 字符
- `llm_client.LLMClientError` 原样向上抛，由 generate 层兜底

---

### `backend/application/reports/guard.py` — 反原文引用校验

```python
VERBATIM_QUOTE_THRESHOLD = 12

def check_no_verbatim_quote(
    report_payload: dict,
    source_sessions: list[SessionRecord],
    blocked_user_ids: list[str] | None = None,
) -> bool
```

- 拼接 source sessions 的 `description + feeling` 作为原始语料
- 对 `weather.narrative`、`weather.tags.*` 与所有 `resonance.*` 用户可见文本做最长公共子串检测
- 任一连续重合片段长度 `>= VERBATIM_QUOTE_THRESHOLD` 返回 False
- 若传入 `blocked_user_ids`，对上述 LLM 生成的用户可见文本做真实 `user_id` 黑名单扫描；任一命中返回 False
- 返回 True 表示通过，可进入 `status="ready"` 持久化

---

### `backend/application/reports/generate.py` — 周报生成用例

```python
def generate_weekly_report(
    couple_id: str,
    window_end: datetime | None = None,
) -> Report
```

- `window_end` 为空时取当前时间
- window 起点为 `window_end - Couple.weekly_report_interval_days`
- 流程：
  - 校验 `service_active_for_couple(couple_id)`；未启用抛 `ReportGenerationError`
  - 调 `get_shared_sessions_for_rag(couple_id, window)` 获取窗口内 shared sessions
  - 计算 `footprint` 与 `suspense`
  - shared sessions 少于 3 条时跳过 LLM，写入 `status="sparse"` report
  - 数据充足时调用 `extract_semantic(sessions, couple)` 并拼装四模块 payload
  - LLM 失败时写入 `status="failed"` report，不向 UI/cron 抛出
  - guard 不通过时写入 `status="failed"` report，不保存 weather/resonance 正文；包含原文长引用或 LLM 生成可见文本泄露本次 source sessions 中真实 `user_id`
  - guard 通过时写入 `status="ready"` report
- `model_version` 写入 DeepSeek 客户端当前模型名
- `source_session_ids` 对 sparse / ready / failed 均写入，便于审计与排障
- `report_id` 使用 `rpt_YYYYMMDD_<couple_id>`；同日同 couple 重复手动生成会覆盖同一 report
