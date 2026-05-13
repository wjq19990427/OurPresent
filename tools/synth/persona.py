"""Persona card loading for the synthetic data workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_PERSONA_PATH = Path(__file__).resolve().parent / "personas" / "lin_xia_together.json"
OUTCOMES = {"together", "destroyed"}


def load_persona_seed(path: Path | None = None) -> dict[str, Any]:
    persona_path = path or DEFAULT_PERSONA_PATH
    with persona_path.open("r", encoding="utf-8") as handle:
        seed = json.load(handle)
    validate_persona_seed(seed)
    return seed


def validate_persona_seed(seed: dict[str, Any]) -> None:
    for key in ("seed_id", "start_date", "a", "b"):
        if key not in seed:
            raise ValueError(f"persona seed missing required field: {key}")
    if seed.get("expected_outcome") is not None and seed["expected_outcome"] not in OUTCOMES:
        raise ValueError("persona expected_outcome must be together or destroyed")

    required = {
        "id",
        "username",
        "display_name",
        "tone",
        "communication_style",
        "relationship_stage",
        "emotional_anchors",
    }
    for side in ("a", "b"):
        card = seed.get(side)
        if not isinstance(card, dict):
            raise ValueError(f"persona seed missing persona {side}")
        missing = sorted(required - set(card))
        if missing:
            raise ValueError(f"persona {card.get('id', side)} missing fields: {missing}")
        if not isinstance(card["emotional_anchors"], list) or not card["emotional_anchors"]:
            raise ValueError(f"persona {card.get('id', side)} must contain emotional_anchors")
