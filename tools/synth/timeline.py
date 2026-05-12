"""Timeline generation for synthetic couple memories."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from tools.synth.minimax_client import MinimaxClient
from tools.synth.persona import primary_couple


def generate_timeline(
    persona_seed: dict[str, Any],
    weeks: int = 6,
    client: MinimaxClient | None = None,
) -> list[dict[str, Any]]:
    if weeks < 4 or weeks > 12:
        raise ValueError("weeks must be between 4 and 12")
    if client is None:
        return deterministic_timeline(persona_seed, weeks)
    payload = client.generate_json(_timeline_prompt(persona_seed, weeks))
    events = payload.get("events")
    if not isinstance(events, list):
        raise ValueError("Minimax timeline response must contain an events list")
    validate_timeline(events)
    return events


def deterministic_timeline(persona_seed: dict[str, Any], weeks: int) -> list[dict[str, Any]]:
    couple = primary_couple(persona_seed)
    anchor = date.fromisoformat(persona_seed.get("start_date", "2026-01-05"))
    themes = [
        (
            "shared",
            "周一早晨一起整理新家厨房",
            "我想把生活过得有秩序，也怕自己的急躁吓到对方。",
            "我感到被照顾，也担心自己跟不上对方的节奏。",
        ),
        (
            "A",
            "项目上线前的深夜加班",
            "我很疲惫，但不想把压力全部倒给伴侣。",
            "我想靠近，却不知道怎样不打扰。",
        ),
        (
            "B",
            "临时取消的周末短途旅行",
            "我知道计划被打乱不是谁的错，可还是有点失落。",
            "我表面说没关系，其实很想被认真安慰。",
        ),
        (
            "shared",
            "读到一条旧消息后的误会",
            "我害怕被误解，于是说话变硬了。",
            "我听见的是防备，不是解释。",
        ),
        (
            "A",
            "给对方准备没有说出口的小礼物",
            "我想慢慢修补，不想显得像在讨好。",
            "我隐约感到对方在努力，但还没准备好回应。",
        ),
        (
            "B",
            "一次共享记录被读到后的回复",
            "我终于敢把那天的心情放出来一点。",
            "读到以后我很心疼，也更愿意下一次先问清楚。",
        ),
        (
            "shared",
            "月末一起复盘关系节奏",
            "我希望我们的亲密可以不靠猜。",
            "我希望被看见的同时，也保留自己的空间。",
        ),
        (
            "A",
            "雨天在地铁站等到对方",
            "我发现自己还是很珍惜这些普通时刻。",
            "我愿意把紧张放慢一点。",
        ),
    ]
    step_days = max(3, (weeks * 7) // len(themes))
    events: list[dict[str, Any]] = []
    for index, (perspective, theme, feeling_a, feeling_b) in enumerate(themes):
        day = anchor + timedelta(days=index * step_days)
        events.append(
            {
                "id": f"evt_{index + 1:02d}",
                "date": day.isoformat(),
                "perspective": perspective,
                "theme": theme,
                "seed_from": "sess_06_share_now" if index == 5 else None,
                "inner_voice": {
                    "A": f"{couple['a']['display_name']}：{feeling_a}",
                    "B": f"{couple['b']['display_name']}：{feeling_b}",
                },
            }
        )
    return events


def validate_timeline(events: list[dict[str, Any]]) -> None:
    for event in events:
        missing = {"id", "date", "perspective", "theme", "inner_voice"} - set(event)
        if missing:
            raise ValueError(f"timeline event missing fields: {sorted(missing)}")
        voices = event["inner_voice"]
        if not isinstance(voices, dict) or not voices.get("A") or not voices.get("B"):
            raise ValueError(f"timeline event {event.get('id')} must contain A/B inner voices")


def _timeline_prompt(persona_seed: dict[str, Any], weeks: int) -> str:
    return (
        "你是 OurPresent 的合成数据编剧。请基于以下情侣角色卡生成 "
        f"{weeks} 周的双视角事件时间线，只返回 JSON："
        '{"events":[{"id":"evt_01","date":"YYYY-MM-DD","perspective":"A|B|shared",'
        '"theme":"...","inner_voice":{"A":"...","B":"..."}}]}。\n\n'
        + json.dumps(persona_seed, ensure_ascii=False, indent=2)
    )
