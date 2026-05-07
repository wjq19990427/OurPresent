from __future__ import annotations

from pathlib import Path

import pytest

from backend.application.sessions import creation, editing, files, markdown
from backend.config import settings
from backend.infrastructure.database import db as db_module


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "data"
    assets_dir = tmp_path / "Assets"
    pending_dir = assets_dir / "Pending"
    final_dir = assets_dir / "Final"
    db_path = data_dir / "db.json"

    for path in (data_dir, pending_dir, final_dir):
        path.mkdir(parents=True, exist_ok=True)

    patches = [
        (settings, "BASE_DIR", tmp_path),
        (settings, "DATA_DIR", data_dir),
        (settings, "DB_PATH", db_path),
        (settings, "ASSETS_DIR", assets_dir),
        (settings, "PENDING_DIR", pending_dir),
        (settings, "FINAL_DIR", final_dir),
        (db_module, "DATA_DIR", data_dir),
        (db_module, "DB_PATH", db_path),
        (db_module, "PENDING_DIR", pending_dir),
        (db_module, "FINAL_DIR", final_dir),
        (creation, "PENDING_DIR", pending_dir),
        (creation, "FINAL_DIR", final_dir),
        (editing, "FINAL_DIR", final_dir),
        (files, "FINAL_DIR", final_dir),
        (markdown, "FINAL_DIR", final_dir),
    ]
    for module, attr, value in patches:
        monkeypatch.setattr(module, attr, value)

    return tmp_path
