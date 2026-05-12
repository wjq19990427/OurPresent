"""Persona card loading for the synthetic data workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_PERSONA_PATH = Path(__file__).resolve().parent / "personas" / "sample_couples.json"


def load_persona_seed(path: Path | None = None) -> dict[str, Any]:
    persona_path = path or DEFAULT_PERSONA_PATH
    with persona_path.open("r", encoding="utf-8") as handle:
        seed = json.load(handle)
    validate_persona_seed(seed)
    return seed


def validate_persona_seed(seed: dict[str, Any]) -> None:
    couples = seed.get("couples")
    if not isinstance(couples, list) or not couples:
        raise ValueError("persona seed must contain at least one couple")

    required = {
        "id",
        "display_name",
        "tone",
        "communication_style",
        "relationship_stage",
        "emotional_anchors",
    }
    for couple in couples:
        for side in ("a", "b"):
            card = couple.get(side)
            if not isinstance(card, dict):
                raise ValueError(f"couple {couple.get('id', '<unknown>')} missing persona {side}")
            missing = sorted(required - set(card))
            if missing:
                raise ValueError(f"persona {card.get('id', side)} missing fields: {missing}")


def primary_couple(seed: dict[str, Any]) -> dict[str, Any]:
    for couple in seed["couples"]:
        if couple.get("role") == "primary":
            return couple
    return seed["couples"][0]
