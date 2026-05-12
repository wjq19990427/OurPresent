"""Command helpers shared by run_synth.py and replay.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_script(script: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{script['metadata']['name']}.json"
    text = json.dumps(script, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(text, encoding="utf-8")
    return path


def read_script(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
