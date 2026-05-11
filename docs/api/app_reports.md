### `backend/application/reports/*` — 情感周报

本 L2 契约目前仅记录 task-7 已落地的数据底座：`Report` 领域模型与 `reports_repo`。周报生成、查询用例、LLM 接入、调度与 UI 渲染将在 task-8 / task-9 及后续任务中补齐。

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
