"""Delayed-share action script generation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from tools.synth.persona import primary_couple

TIME_FMT = "%Y-%m-%d %H:%M:%S"


def build_script(
    persona_seed: dict[str, Any],
    timeline: list[dict[str, Any]],
    weeks: int,
) -> dict[str, Any]:
    base = datetime.fromisoformat(f"{timeline[0]['date']} 09:00:00")
    return {
        "schema_version": 1,
        "metadata": {
            "name": "任务20_合成数据剧本",
            "weeks": weeks,
            "generated_at": base.strftime(TIME_FMT),
            "notes": "人可读剧本；重放时不调用大模型。",
        },
        "personas": persona_seed,
        "timeline": timeline,
        "couples": [
            _couple_entry(primary_couple(persona_seed), "primary"),
            _couple_entry(_destroy_couple(persona_seed), "destroy_sample"),
        ],
        "sessions": _session_actions(timeline, base),
        "destroy_actions": [
            {
                "id": "destroy_01",
                "couple_ref": "destroy_sample",
                "initiator": "A",
                "start_uncouple_at": (base + timedelta(days=45, hours=9)).strftime(TIME_FMT),
                "destroy_at": (base + timedelta(days=45, hours=10)).strftime(TIME_FMT),
                "reason": "冻结期销毁分支样本：先冻结，再调用 destroy_couple_data 完整清理。",
            }
        ],
        "coverage": {
            "covered": [
                "永久私密",
                "延时共享_1小时",
                "延时共享_1天",
                "延时共享_1周",
                "延时共享_1个月",
                "调整解锁时间_推后",
                "调整解锁时间_提前",
                "立即解锁",
                "伴侣读取后评论互动",
                "冻结期销毁完整链路",
            ],
            "skipped": [],
        },
    }


def _destroy_couple(seed: dict[str, Any]) -> dict[str, Any]:
    for couple in seed["couples"]:
        if couple.get("role") == "destroy_sample":
            return couple
    return seed["couples"][-1]


def _couple_entry(couple: dict[str, Any], ref: str) -> dict[str, Any]:
    return {"ref": ref, "a": couple["a"], "b": couple["b"], "password": "synth-pass-20"}


def _session_actions(timeline: list[dict[str, Any]], base: datetime) -> list[dict[str, Any]]:
    specs = [
        ("sess_01_private", "primary", "A", 0, "private", []),
        (
            "sess_02_pending_1h",
            "primary",
            "B",
            1,
            "pending_unlock",
            [{"type": "request_unlock", "at_offset_hours": 1, "unlock_after": {"hours": 2}}],
        ),
        (
            "sess_03_pending_1d",
            "primary",
            "A",
            2,
            "pending_unlock",
            [{"type": "request_unlock", "at_offset_hours": 1, "unlock_after": {"days": 1}}],
        ),
        (
            "sess_04_reschedule_later",
            "primary",
            "B",
            3,
            "pending_unlock",
            [
                {"type": "request_unlock", "at_offset_hours": 1, "unlock_after": {"days": 7}},
                {
                    "type": "reschedule_unlock",
                    "at_offset_hours": 2,
                    "unlock_after": {"days": 14},
                },
            ],
        ),
        (
            "sess_05_reschedule_earlier_1m",
            "primary",
            "A",
            4,
            "pending_unlock",
            [
                {"type": "request_unlock", "at_offset_hours": 1, "unlock_after": {"days": 45}},
                {
                    "type": "reschedule_unlock",
                    "at_offset_hours": 2,
                    "unlock_after": {"days": 31},
                },
            ],
        ),
        (
            "sess_06_share_now",
            "primary",
            "B",
            5,
            "shared",
            [
                {"type": "request_unlock", "at_offset_hours": 1, "unlock_after": {"days": 7}},
                {"type": "unlock_now", "at_offset_hours": 2},
                {
                    "type": "add_comment",
                    "at_offset_hours": 3,
                    "author": "A",
                    "text": "我读到了，也终于明白那天你不是冷淡，是怕打扰我。",
                },
            ],
        ),
        ("sess_07_destroy_seed", "destroy_sample", "A", 6, "destroyed", []),
    ]
    sessions: list[dict[str, Any]] = []
    for index, (ref, couple_ref, author, event_index, branch, actions) in enumerate(specs):
        event = timeline[event_index]
        created_at = base + timedelta(days=index, minutes=index)
        sessions.append(
            {
                "ref": ref,
                "couple_ref": couple_ref,
                "author": author,
                "event_id": event["id"],
                "branch": branch,
                "created_at": created_at.strftime(TIME_FMT),
                "source_type": "text",
                "fields": {
                    "content_time": event["date"],
                    "description": event["theme"],
                    "feeling": event["inner_voice"][author],
                    "reason": _reason_for_branch(branch),
                },
                "actions": [_expand_action(created_at, action) for action in actions],
            }
        )
    return sessions


def _expand_action(created_at: datetime, action: dict[str, Any]) -> dict[str, Any]:
    expanded = dict(action)
    action_at = created_at + timedelta(hours=action.get("at_offset_hours", 0))
    expanded["at"] = action_at.strftime(TIME_FMT)
    expanded.pop("at_offset_hours", None)
    if "unlock_after" in action:
        unlock_at = created_at + timedelta(**action["unlock_after"])
        expanded["unlock_at"] = unlock_at.strftime(TIME_FMT)
        expanded.pop("unlock_after", None)
    return expanded


def _reason_for_branch(branch: str) -> str:
    return {
        "private": "这是一段只想先放在自己心里的记录。",
        "pending_unlock": "想让对方稍后看到，而不是在情绪最满的时候立刻共享。",
        "shared": "决定提前把话说开，给下一次互动一个入口。",
        "destroyed": "用于验证冻结期销毁链路，不保留关系内记录。",
    }[branch]
