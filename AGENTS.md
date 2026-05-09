# AGENTS.md

This file gives future coding agents quick context for working in this repository.

## Project Summary

- Project name: `OurPresent`
- Current stage: local `Streamlit` alpha demo
- Product goal: a private two-person memory space for couples, with delayed sharing, relationship-bound privacy controls, export, freeze, and destruction flows
- Runtime: Python `3.9+`

## Tech Stack

- Frontend shell: `Streamlit`
- Backend language: `Python`
- Storage (current alpha): `data/database.db` plus local media under `Assets/`
- Legacy storage: if `data/db.json` exists, it is auto-migrated into SQLite on startup
- Tooling: `uv`, `pytest`, `ruff`

## Common Commands

Install dependencies:

```bash
uv sync
```

Run the app:

```bash
uv run streamlit run main.py
```

Lint:

```bash
uv run ruff check .
```

Tests:

```bash
uv run pytest
```

## Repository Shape

- `main.py`: Streamlit entry point
- `frontend/streamlit_app/`: Streamlit UI code
- `backend/application/`: use cases and orchestration
- `backend/domain/`: core business models and rules
- `backend/infrastructure/`: persistence, media, and integration details
- `backend/config/`: configuration
- `backend/tests/`: automated tests
- `docs/`: product and technical documentation
- `data/`: local demo data
- `Assets/`: uploaded or managed media assets

## Working Rules

- Prefer small, targeted edits that preserve the current alpha demo behavior
- Keep architectural boundaries clear: avoid pushing infrastructure concerns into `domain`
- Treat privacy and relationship-state logic as sensitive product behavior; avoid changing it casually
- If a behavior change is user-visible, update tests when practical
- Reuse existing patterns before introducing new abstractions
- Prefer reading `docs/PRD.md`, `docs/technical-report.md`, and `docs/api-contracts.md` before making larger changes

## Testing Expectations

- Run `uv run ruff check .` after meaningful Python changes
- Run `uv run pytest` when logic or data flow changes
- If you cannot run verification, say so clearly in the final handoff

## Notes For Future Agents

- This repo appears to be an alpha prototype, so prioritize clarity, stability, and fast iteration over premature generalization
- The most likely high-risk areas are privacy rules, time-lock sharing, couple binding state, and destructive data flows
- When uncertain about intent, inspect the docs first instead of guessing
