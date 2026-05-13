"""Command helpers shared by run_synth.py and replay.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.synth.script_io import dump_md, load_md


def write_script(script: dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / f"{script['metadata']['name']}.md"
    return dump_md(script, path)


def read_script(path: Path) -> dict[str, Any]:
    return load_md(path)
