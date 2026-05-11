### `backend/infrastructure/ai/agent_skills.py` — AI 集成边界

第二阶段 AI 接口预留，当前仍是占位实现。

```python
def get_shared_sessions_for_rag(couple_id: str) -> list[dict]
```

- 返回指定情侣关系下所有 `visibility == "shared"` 的 sessions
- 供未来 RAG / 向量索引使用
- 强约束：私密记录不能进入向量库

```python
def get_report_history(couple_id: str) -> list[dict]
```

- 情感周报历史薄包装
- 委托 `backend.application.reports.query.list_reports(couple_id)`
- 返回 `Report.to_dict()` 列表，排序由 query/repository 保证为 `generated_at` 倒序
- 包含 `failed`，便于未来排障入口使用
