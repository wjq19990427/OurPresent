"""Markdown script serialization for the synth workflow."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

TIME_FMT = "%Y-%m-%d %H:%M:%S"
TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FENCE_RE = re.compile(r"^```yaml +(timeline|session|destroy_actions)\n(.*?)^```", re.M | re.S)
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)

FRONTMATTER_KEYS = (
    "schema_version",
    "outcome",
    "outcome_reason",
    "metadata",
    "personas",
    "couples",
    "coverage",
)
OUTCOMES = {"together", "destroyed"}
ACTION_TYPES = {"request_unlock", "reschedule_unlock", "unlock_now", "add_comment"}


class ScriptFormatError(ValueError):
    """Raised when a Markdown synth script cannot be parsed or validated."""


def dump_md(script: dict[str, Any], path: Path) -> Path:
    validate_script(script)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_md(script), encoding="utf-8")
    return path


def load_md(path: Path) -> dict[str, Any]:
    return loads_md(path.read_text(encoding="utf-8"))


def dumps_md(script: dict[str, Any]) -> str:
    validate_script(script)
    frontmatter = {key: deepcopy(script[key]) for key in FRONTMATTER_KEYS}
    lines = [
        "---",
        *_dump_yaml(frontmatter),
        "---",
        "",
        f"# {script['metadata']['name']}",
        "",
        f"结局：`{script['outcome']}`。{script['outcome_reason']}",
        "",
        "这份 Markdown 是合成数据的唯一剧本来源。上方 frontmatter 放角色卡、关系",
        "和覆盖范围等结构字段；下方正文按时间顺序排列事件、记录和后续行为。",
        "",
        "编辑时优先改每个 `session` 代码块里的 `fields.description`、",
        "`fields.feeling`、`fields.reason`，不要改 `schema_version` 或关系引用字段，",
        "除非你确实要改变剧本结构。",
        "",
        "## 时间线与记录",
        "",
    ]

    sessions_by_event = _sessions_by_event(script["sessions"])
    for event in script["timeline"]:
        lines.extend(_event_section(event, sessions_by_event.get(event["id"], [])))

    lines.extend(
        [
            "## 关系解除与数据销毁动作",
            "",
            "这里描述需要先进入解除关系冻结期、再销毁这对关系内数据的动作。",
            "列表为空时表示这份剧本不验证销毁流程。",
            "",
            "```yaml destroy_actions",
            *_dump_yaml(script.get("destroy_actions", [])),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def loads_md(text: str) -> dict[str, Any]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ScriptFormatError("Markdown script must start with frontmatter delimited by ---")

    frontmatter = _parse_yaml(match.group(1))
    if not isinstance(frontmatter, dict):
        raise ScriptFormatError("frontmatter must be a mapping")

    blocks: dict[str, list[Any]] = {"timeline": [], "session": [], "destroy_actions": []}
    for block_type, block_text in FENCE_RE.findall(text[match.end() :]):
        parsed = _parse_yaml(block_text)
        blocks[block_type].append(parsed)

    if not blocks["timeline"]:
        raise ScriptFormatError("Markdown script must contain at least one yaml timeline block")
    if not blocks["session"]:
        raise ScriptFormatError("Markdown script must contain at least one yaml session block")
    if len(blocks["destroy_actions"]) > 1:
        raise ScriptFormatError("Markdown script may contain only one yaml destroy_actions block")

    destroy_actions = blocks["destroy_actions"][0] if blocks["destroy_actions"] else []
    script = {
        **frontmatter,
        "timeline": blocks["timeline"],
        "sessions": blocks["session"],
        "destroy_actions": destroy_actions,
    }
    validate_script(script)
    return script


def validate_script(script: dict[str, Any]) -> None:
    _require_mapping(script, "script")
    for key in FRONTMATTER_KEYS:
        if key not in script:
            raise ScriptFormatError(f"script missing required field: {key}")
    if script["outcome"] not in OUTCOMES:
        raise ScriptFormatError("script.outcome must be together or destroyed")
    _require_text(script["outcome_reason"], "script.outcome_reason")

    metadata = _require_mapping(script["metadata"], "metadata")
    for key in ("name", "weeks", "generated_at"):
        _require_key(metadata, key, "metadata")
    _require_time(metadata["generated_at"], "metadata.generated_at")

    personas = _require_mapping(script["personas"], "personas")
    _validate_persona_pair(personas, "personas")

    couples = _require_list(script["couples"], "couples")
    couple_refs: set[str] = set()
    for index, couple in enumerate(couples):
        mapping = _require_mapping(couple, f"couples[{index}]")
        for key in ("ref", "a", "b", "password"):
            _require_key(mapping, key, f"couples[{index}]")
        couple_refs.add(_require_text(mapping["ref"], f"couples[{index}].ref"))
        for side in ("a", "b"):
            card = _require_mapping(mapping[side], f"couples[{index}].{side}")
            _require_key(card, "username", f"couples[{index}].{side}")

    timeline = _require_list(script.get("timeline"), "timeline")
    event_ids: set[str] = set()
    for index, event in enumerate(timeline):
        mapping = _require_mapping(event, f"timeline[{index}]")
        for key in ("id", "date", "perspective", "theme", "inner_voice"):
            _require_key(mapping, key, f"timeline[{index}]")
        event_id = _require_text(mapping["id"], f"timeline[{index}].id")
        event_ids.add(event_id)
        _require_date(mapping["date"], f"timeline[{index}].date")
        voices = _require_mapping(mapping["inner_voice"], f"timeline[{index}].inner_voice")
        for side in ("A", "B"):
            _require_text(voices.get(side), f"timeline[{index}].inner_voice.{side}")

    sessions = _require_list(script.get("sessions"), "sessions")
    for index, session in enumerate(sessions):
        _validate_session(session, index, event_ids, couple_refs)

    destroy_actions = _require_list(script.get("destroy_actions", []), "destroy_actions")
    for index, action in enumerate(destroy_actions):
        _validate_destroy_action(action, index, couple_refs)

    _require_mapping(script["coverage"], "coverage")


def _event_section(event: dict[str, Any], sessions: list[dict[str, Any]]) -> list[str]:
    seed_from = event.get("seed_from") or "无"
    lines = [
        f"### {event['date']} · {event['id']} · {event['theme']}",
        "",
        f"- 事件视角：`{event['perspective']}`",
        f"- 由哪条记录继续发展：{seed_from}",
        f"- A 的内心：{event['inner_voice']['A']}",
        f"- B 的内心：{event['inner_voice']['B']}",
        "",
        "```yaml timeline",
        *_dump_yaml(event),
        "```",
        "",
    ]
    if not sessions:
        lines.extend(["这一天没有要写入数据库的记录。", ""])
        return lines

    for session in sessions:
        lines.extend(
            [
                f"#### {session['ref']} · 作者 {session['author']} · {session['branch']}",
                "",
                f"- 写入关系：`{session['couple_ref']}`",
                f"- 创建时间：`{session['created_at']}`",
                f"- 描述：{session['fields']['description']}",
                f"- 感受：{session['fields']['feeling']}",
                f"- 选择这个公开状态的原因：{session['fields']['reason']}",
                "",
                "```yaml session",
                *_dump_yaml(session),
                "```",
                "",
            ]
        )
    return lines


def _sessions_by_event(sessions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for session in sessions:
        grouped.setdefault(session["event_id"], []).append(session)
    return grouped


def _dump_yaml(value: Any, indent: int = 0) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, child in value.items():
            if _is_scalar(child) or child == []:
                lines.append(f"{prefix}{key}: {_format_scalar(child)}")
            else:
                lines.append(f"{prefix}{key}:")
                lines.extend(_dump_yaml(child, indent + 2))
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{prefix}[]"]
        lines = []
        for item in value:
            if isinstance(item, dict):
                items = list(item.items())
                if not items:
                    lines.append(f"{prefix}- {{}}")
                    continue
                first_key, first_value = items[0]
                if _is_scalar(first_value) or first_value == []:
                    lines.append(f"{prefix}- {first_key}: {_format_scalar(first_value)}")
                else:
                    lines.append(f"{prefix}- {first_key}:")
                    lines.extend(_dump_yaml(first_value, indent + 4))
                for key, child in items[1:]:
                    if _is_scalar(child) or child == []:
                        lines.append(f"{prefix}  {key}: {_format_scalar(child)}")
                    else:
                        lines.append(f"{prefix}  {key}:")
                        lines.extend(_dump_yaml(child, indent + 4))
            else:
                lines.append(f"{prefix}- {_format_scalar(item)}")
        return lines
    return [f"{prefix}{_format_scalar(value)}"]


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if value == []:
        return "[]"
    if not isinstance(value, str):
        raise ScriptFormatError(f"unsupported scalar type: {type(value).__name__}")
    if _can_be_plain(value):
        return value
    return json.dumps(value, ensure_ascii=False)


def _can_be_plain(value: str) -> bool:
    if value == "":
        return False
    lowered = value.lower()
    if lowered in {"null", "true", "false", "[]", "{}"}:
        return False
    if value[0] in {"-", "{", "}", "[", "]", "#", '"', "'", "`", "|", ">", "!", "&", "*", "@"}:
        return False
    if "\n" in value or "\r" in value:
        return False
    return not re.fullmatch(r"-?\d+", value)


def _parse_yaml(text: str) -> Any:
    lines = _yaml_lines(text)
    if not lines:
        return {}
    value, index = _parse_block(lines, lines[0][0], 0)
    if index != len(lines):
        raise ScriptFormatError(f"unexpected yaml content: {lines[index][1]}")
    return value


def _yaml_lines(text: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or raw.lstrip().startswith("<!--"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2 != 0:
            raise ScriptFormatError(f"yaml indentation must use two spaces: {raw}")
        result.append((indent, raw.strip()))
    return result


def _parse_block(lines: list[tuple[int, str]], indent: int, index: int) -> tuple[Any, int]:
    current_indent, current = lines[index]
    if current_indent != indent:
        raise ScriptFormatError(f"expected indent {indent}, got {current_indent}: {current}")
    if current.startswith("- ") or current == "[]":
        return _parse_list(lines, indent, index)
    return _parse_dict(lines, indent, index)


def _parse_dict(
    lines: list[tuple[int, str]],
    indent: int,
    index: int,
) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        current_indent, current = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ScriptFormatError(f"unexpected nested yaml line: {current}")
        if current.startswith("- "):
            break
        key, value_text = _split_key_value(current)
        index += 1
        if value_text:
            result[key] = _parse_scalar(value_text)
        elif index < len(lines) and lines[index][0] > indent:
            result[key], index = _parse_block(lines, lines[index][0], index)
        else:
            result[key] = None
    return result, index


def _parse_list(lines: list[tuple[int, str]], indent: int, index: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        current_indent, current = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ScriptFormatError(f"unexpected nested yaml list line: {current}")
        if current == "[]":
            index += 1
            continue
        if not current.startswith("- "):
            break

        item_text = current[2:].strip()
        index += 1
        if not item_text:
            if index >= len(lines) or lines[index][0] <= indent:
                result.append(None)
            else:
                value, index = _parse_block(lines, lines[index][0], index)
                result.append(value)
        elif _looks_like_key_value(item_text):
            item, index = _parse_list_mapping_item(item_text, lines, indent, index)
            result.append(item)
        else:
            result.append(_parse_scalar(item_text))
    return result, index


def _parse_list_mapping_item(
    item_text: str,
    lines: list[tuple[int, str]],
    list_indent: int,
    index: int,
) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    key, value_text = _split_key_value(item_text)
    if value_text:
        result[key] = _parse_scalar(value_text)
    elif index < len(lines) and lines[index][0] > list_indent + 2:
        result[key], index = _parse_block(lines, lines[index][0], index)
    else:
        result[key] = None

    while index < len(lines):
        current_indent, current = lines[index]
        if current_indent <= list_indent:
            break
        if current_indent != list_indent + 2:
            raise ScriptFormatError(f"unexpected yaml list item line: {current}")
        key, value_text = _split_key_value(current)
        index += 1
        if value_text:
            result[key] = _parse_scalar(value_text)
        elif index < len(lines) and lines[index][0] > current_indent:
            result[key], index = _parse_block(lines, lines[index][0], index)
        else:
            result[key] = None
    return result, index


def _split_key_value(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise ScriptFormatError(f"yaml line must be key: value: {line}")
    key, value = line.split(":", 1)
    key = key.strip()
    if not key:
        raise ScriptFormatError(f"yaml key cannot be empty: {line}")
    return key, value.strip()


def _looks_like_key_value(text: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*:", text))


def _parse_scalar(text: str) -> Any:
    if text == "null":
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    if text == "[]":
        return []
    if text == "{}":
        return {}
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if text.startswith('"'):
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ScriptFormatError(f"invalid quoted string: {text}") from exc
    return text


def _validate_persona_pair(value: Any, path: str) -> None:
    couple = _require_mapping(value, path)
    for side in ("a", "b"):
        card = _require_mapping(couple.get(side), f"{path}.{side}")
        for key in (
            "id",
            "username",
            "display_name",
            "tone",
            "communication_style",
            "relationship_stage",
            "emotional_anchors",
        ):
            _require_key(card, key, f"{path}.{side}")
        _require_list(card["emotional_anchors"], f"{path}.{side}.emotional_anchors")


def _validate_session(
    value: Any,
    index: int,
    event_ids: set[str],
    couple_refs: set[str],
) -> None:
    path = f"sessions[{index}]"
    session = _require_mapping(value, path)
    for key in ("ref", "couple_ref", "author", "event_id", "branch", "created_at", "source_type"):
        _require_key(session, key, path)
    _require_time(session["created_at"], f"{path}.created_at")
    if session["couple_ref"] not in couple_refs:
        raise ScriptFormatError(
            f"{path}.couple_ref references unknown couple: {session['couple_ref']}"
        )
    if session["event_id"] not in event_ids:
        raise ScriptFormatError(
            f"{path}.event_id references unknown timeline event: {session['event_id']}"
        )
    fields = _require_mapping(session.get("fields"), f"{path}.fields")
    for key in ("content_time", "description", "feeling", "reason"):
        _require_text(fields.get(key), f"{path}.fields.{key}")
    _require_date(fields["content_time"], f"{path}.fields.content_time")
    actions = _require_list(session.get("actions", []), f"{path}.actions")
    for action_index, action in enumerate(actions):
        _validate_session_action(action, f"{path}.actions[{action_index}]")


def _validate_session_action(value: Any, path: str) -> None:
    action = _require_mapping(value, path)
    action_type = _require_text(action.get("type"), f"{path}.type")
    if action_type not in ACTION_TYPES:
        raise ScriptFormatError(f"{path}.type is unsupported: {action_type}")
    _require_time(action.get("at"), f"{path}.at")
    if action_type in {"request_unlock", "reschedule_unlock"}:
        _require_time(action.get("unlock_at"), f"{path}.unlock_at")
        action_at = datetime.strptime(action["at"], TIME_FMT)
        unlock_at = datetime.strptime(action["unlock_at"], TIME_FMT)
        if unlock_at <= action_at:
            raise ScriptFormatError(f"{path}.unlock_at must be later than {path}.at")
    if action_type == "add_comment":
        if action.get("author") not in {"A", "B"}:
            raise ScriptFormatError(f"{path}.author must be A or B")
        _require_text(action.get("text"), f"{path}.text")


def _validate_destroy_action(value: Any, index: int, couple_refs: set[str]) -> None:
    path = f"destroy_actions[{index}]"
    action = _require_mapping(value, path)
    for key in ("id", "couple_ref", "initiator", "start_uncouple_at", "destroy_at", "reason"):
        _require_key(action, key, path)
    if action["couple_ref"] not in couple_refs:
        raise ScriptFormatError(
            f"{path}.couple_ref references unknown couple: {action['couple_ref']}"
        )
    if action["initiator"] not in {"A", "B"}:
        raise ScriptFormatError(f"{path}.initiator must be A or B")
    _require_time(action["start_uncouple_at"], f"{path}.start_uncouple_at")
    _require_time(action["destroy_at"], f"{path}.destroy_at")


def _require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScriptFormatError(f"{path} must be a mapping")
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ScriptFormatError(f"{path} must be a list")
    return value


def _require_key(mapping: dict[str, Any], key: str, path: str) -> None:
    if key not in mapping:
        raise ScriptFormatError(f"{path} missing required field: {key}")


def _require_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise ScriptFormatError(f"{path} must be a non-empty string")
    return value


def _require_time(value: Any, path: str) -> None:
    text = _require_text(value, path)
    if not TIME_RE.match(text):
        raise ScriptFormatError(f"{path} must use YYYY-MM-DD HH:MM:SS")


def _require_date(value: Any, path: str) -> None:
    text = _require_text(value, path)
    if not DATE_RE.match(text):
        raise ScriptFormatError(f"{path} must use YYYY-MM-DD")


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, bool))
