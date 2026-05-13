"""Replay an existing synth script without calling an LLM."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.synth.cli import read_script
from tools.synth.driver import run_script, summarize_sqlite


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay an OurPresent synth script Markdown file.")
    parser.add_argument("script", type=Path)
    parser.add_argument(
        "--append",
        action="store_true",
        help="Do not reset the isolated synth DB first.",
    )
    args = parser.parse_args()

    script = read_script(args.script)
    db_path = run_script(script, reset_db=not args.append)
    print(f"db={db_path}")
    print(f"summary={summarize_sqlite(db_path)}")


if __name__ == "__main__":
    main()
