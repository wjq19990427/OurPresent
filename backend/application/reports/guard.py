"""Privacy guards for generated weekly reports."""

from __future__ import annotations

from backend.domain.models import SessionRecord

VERBATIM_QUOTE_THRESHOLD = 12


def _longest_common_substring_length(left: str, right: str) -> int:
    if not left or not right:
        return 0

    previous = [0] * (len(right) + 1)
    best = 0
    for left_char in left:
        current = [0] * (len(right) + 1)
        for index, right_char in enumerate(right, start=1):
            if left_char == right_char:
                current[index] = previous[index - 1] + 1
                best = max(best, current[index])
        previous = current
    return best


def _source_text(sessions: list[SessionRecord]) -> str:
    return "\n".join(
        f"{session.description or ''}\n{session.feeling or ''}" for session in sessions
    )


def _generated_visible_text(report_payload: dict) -> list[str]:
    weather = report_payload.get("weather", {})
    candidates = []
    if isinstance(weather, dict):
        candidates.append(str(weather.get("narrative", "")))
        for tag in weather.get("tags", []):
            if isinstance(tag, dict):
                candidates.extend(str(value) for value in tag.values())

    for item in report_payload.get("resonance", []):
        if isinstance(item, dict):
            candidates.append(str(item.get("day", "")))
            candidates.append(str(item.get("topic", "")))
            candidates.append(str(item.get("user_a_excerpt", "")))
            candidates.append(str(item.get("user_b_excerpt", "")))

    return [candidate for candidate in candidates if candidate]


def _contains_blocked_user_id(candidates: list[str], blocked_user_ids: list[str]) -> bool:
    blocked = {user_id for user_id in blocked_user_ids if user_id}
    return any(user_id in candidate for user_id in blocked for candidate in candidates)


def check_no_verbatim_quote(
    report_payload: dict,
    source_sessions: list[SessionRecord],
    blocked_user_ids: list[str] | None = None,
) -> bool:
    """Return True when generated text passes privacy guards."""

    candidates = _generated_visible_text(report_payload)
    if _contains_blocked_user_id(candidates, blocked_user_ids or []):
        return False

    source = _source_text(source_sessions)
    return all(
        _longest_common_substring_length(candidate, source) < VERBATIM_QUOTE_THRESHOLD
        for candidate in candidates
    )
