### `backend/infrastructure/ai/agent_skills.py` — AI 集成边界

```python
def get_shared_sessions_for_rag(
    couple_id: str,
    window: tuple[datetime, datetime] | None = None,
) -> list[dict]
```

- 返回指定情侣关系下所有 `visibility == "shared"` 的 sessions
- 供未来 RAG / 向量索引使用
- 强约束：私密记录不能进入向量库
- `window` 为空时保持全量 shared 行为；传入 `(start, end)` 时按 `shared_at ∈ [start, end]` 过滤
- 返回值仍是 repository 边界的 dict，不在本层转换为 domain model

```python
def get_report_history(couple_id: str, include_failed: bool = False) -> list[dict]
```

- 情感周报历史薄包装
- 委托 `backend.application.reports.query.list_reports(couple_id)`
- 返回 `Report.to_dict()` 列表，排序由 query/repository 保证为 `generated_at` 倒序
- 默认过滤 `status == "failed"`，与 UI 默认可见历史语义一致，避免失败报告进入智能体上下文
- `include_failed=True` 时返回包含 failed 的完整历史，供排障 / 调试入口显式使用

---

### `backend/infrastructure/ai/llm_client.py` — DeepSeek 客户端

```python
class LLMClientError(RuntimeError)
```

- DeepSeek 请求失败、缺少 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` scheme 非 https、响应不是合法结构化 JSON 时抛出
- 上层周报生成用例捕获该异常并写入 `status="failed"` report

```python
@dataclass
class EmotionTag:
    label: str
    weight: float
    phase: str

@dataclass
class ResonanceCandidate:
    day: str
    topic: str
    user_a_text: str
    user_b_text: str

@dataclass
class ResonanceItem:
    day: str
    topic: str
    user_a_excerpt: str
    user_b_excerpt: str
```

- `EmotionTag` 用于 weather.tags
- `ResonanceCandidate` 是 semantic 层传给 LLM 的同日候选，字段已脱敏，不含 session_id / couple_id / 文件路径
- `ResonanceItem` 对齐 report.resonance 输出，excerpt 在客户端/semantic 层截断到 8 字符以内

```python
def extract_emotions(corpus: list[str]) -> list[EmotionTag]
def extract_resonance(items: list[ResonanceCandidate]) -> list[ResonanceItem]
def compose_weather_narrative(tags: list[EmotionTag]) -> str
```

- 三个函数均调用 DeepSeek OpenAI-compatible chat completions API
- API key 优先从环境变量 `DEEPSEEK_API_KEY` 读取；若不存在，读取项目根 `.env` 中同名变量
- 默认模型名为 `deepseek-v4-flash`，可用 `DEEPSEEK_MODEL` 覆盖；`model_version` 会写入 report
- `DEEPSEEK_BASE_URL` 可覆盖默认 endpoint，但必须是 https scheme，否则启动时抛 `LLMClientError`
- 请求使用 JSON response format；返回后仍做结构化解析与长度截断兜底
