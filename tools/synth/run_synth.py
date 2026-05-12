"""Generate a synth script and write it into an isolated database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.synth.actions import build_script
from tools.synth.cli import write_script
from tools.synth.driver import run_script, summarize_sqlite
from tools.synth.minimax_client import MinimaxClient
from tools.synth.persona import DEFAULT_PERSONA_PATH, load_persona_seed
from tools.synth.timeline import generate_timeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and replay OurPresent synth data.")
    parser.add_argument("--persona", type=Path, default=DEFAULT_PERSONA_PATH)
    parser.add_argument("--weeks", type=int, default=6)
    parser.add_argument("--output-dir", type=Path, default=Path("tools/synth/scripts"))
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip Minimax and use fixture logic.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Do not reset the isolated synth DB first.",
    )
    args = parser.parse_args()

    persona_seed = load_persona_seed(args.persona)
    client = None if args.offline else MinimaxClient()
    timeline = generate_timeline(persona_seed, weeks=args.weeks, client=client)
    script = build_script(persona_seed, timeline, args.weeks)
    script_path = write_script(script, args.output_dir)
    db_path = run_script(script, reset_db=not args.append)
    print(f"script={script_path}")
    print(f"db={db_path}")
    print(f"summary={summarize_sqlite(db_path)}")


if __name__ == "__main__":
    main()
