"""DeepSeek client for weekly report semantic extraction."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
REQUEST_TIMEOUT_SECONDS = 30


class LLMClientError(RuntimeError):
    """Raised when the DeepSeek client cannot return valid structured output."""


@dataclass(slots=True)
class EmotionTag:
    label: str
    weight: float
    phase: str


@dataclass(slots=True)
class ResonanceCandidate:
    day: str
    topic: str
    user_a_text: str
    user_b_text: str


@dataclass(slots=True)
class ResonanceItem:
    day: str
    topic: str
    user_a_excerpt: str
    user_b_excerpt: str


def _load_dotenv_api_key() -> str | None:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "DEEPSEEK_API_KEY":
            return value.strip().strip("\"'")
    return None


def _api_key() -> str:
    key = os.getenv("DEEPSEEK_API_KEY") or _load_dotenv_api_key()
    if not key:
        raise LLMClientError("DEEPSEEK_API_KEY is not configured")
    return key


def _json_from_text(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def _chat_json(system_prompt: str, user_payload: dict) -> Any:
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise LLMClientError(f"DeepSeek request failed: {exc}") from exc

    try:
        content = raw["choices"][0]["message"]["content"]
        return _json_from_text(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise LLMClientError("DeepSeek returned invalid JSON content") from exc


def _coerce_emotion_tags(value: Any) -> list[EmotionTag]:
    rows = value.get("tags", value) if isinstance(value, dict) else value
    if not isinstance(rows, list):
        raise LLMClientError("emotion response must contain a tags list")

    tags: list[EmotionTag] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label", "")).strip()
        phase = str(row.get("phase", "")).strip() or "middle"
        if not label:
            continue
        try:
            weight = float(row.get("weight", 0))
        except (TypeError, ValueError):
            weight = 0.0
        tags.append(EmotionTag(label=label[:16], weight=max(0.0, min(weight, 1.0)), phase=phase))
    return tags


def _coerce_resonance(value: Any) -> list[ResonanceItem]:
    rows = value.get("items", value) if isinstance(value, dict) else value
    if not isinstance(rows, list):
        raise LLMClientError("resonance response must contain an items list")

    items: list[ResonanceItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        day = str(row.get("day", "")).strip()
        topic = str(row.get("topic", "")).strip()
        user_a_excerpt = str(row.get("user_a_excerpt", "")).strip()[:8]
        user_b_excerpt = str(row.get("user_b_excerpt", "")).strip()[:8]
        if day and topic and user_a_excerpt and user_b_excerpt:
            items.append(
                ResonanceItem(
                    day=day,
                    topic=topic[:20],
                    user_a_excerpt=user_a_excerpt,
                    user_b_excerpt=user_b_excerpt,
                )
            )
    return items


def extract_emotions(corpus: list[str]) -> list[EmotionTag]:
    """Extract weighted emotion tags from sanitized weekly report corpus."""

    result = _chat_json(
        (
            "你是情感周报的语义抽取器。只输出 JSON。抽取 3-6 个情绪标签，"
            "字段为 label、weight、phase。只围绕观察和感受，不评判、不建议、不点名。"
        ),
        {"corpus": corpus},
    )
    return _coerce_emotion_tags(result)


def extract_resonance(items: list[ResonanceCandidate]) -> list[ResonanceItem]:
    """Extract short resonance phrases from sanitized same-day candidate pairs."""

    result = _chat_json(
        (
            "你是情感周报的共鸣抽取器。只输出 JSON。返回 items 数组，字段为 day、topic、"
            "user_a_excerpt、user_b_excerpt。excerpt 必须小于等于 8 个字符，不引用完整原句。"
        ),
        {"items": [asdict(item) for item in items]},
    )
    return _coerce_resonance(result)


def compose_weather_narrative(tags: list[EmotionTag]) -> str:
    """Compose an <=80 character weather-style narrative from emotion tags."""

    result = _chat_json(
        (
            "你是情绪气象站文案器。只输出 JSON，字段 narrative。"
            "不超过 80 字，天气式陈述，不点名，不写建议或祈使句。"
        ),
        {"tags": [asdict(tag) for tag in tags]},
    )
    if not isinstance(result, dict):
        raise LLMClientError("weather response must be an object")
    narrative = str(result.get("narrative", "")).strip()
    if not narrative:
        raise LLMClientError("weather narrative is empty")
    return narrative[:80]
