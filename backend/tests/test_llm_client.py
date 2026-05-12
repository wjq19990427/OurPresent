from __future__ import annotations

from pathlib import Path

import pytest

from backend.infrastructure.ai import llm_client


@pytest.mark.parametrize("base_url", ["http://example.com", "file:///etc/passwd"])
def test_deepseek_base_url_rejects_non_https_scheme(base_url: str) -> None:
    with pytest.raises(llm_client.LLMClientError, match="Illegal base URL") as exc_info:
        llm_client._validate_deepseek_base_url(base_url)

    assert base_url not in str(exc_info.value)


def test_deepseek_base_url_accepts_https() -> None:
    assert (
        llm_client._validate_deepseek_base_url("https://api.deepseek.com")
        == "https://api.deepseek.com"
    )


def test_configured_base_url_uses_default_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)

    assert llm_client._configured_base_url() == "https://api.deepseek.com"


def test_configured_base_url_reads_legal_https_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.com")

    assert llm_client._configured_base_url() == "https://example.com"


def test_load_dotenv_api_key_walks_up_to_project_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    moved_module_dir = project_root / "src" / "deep" / "nested" / "ai"
    moved_module_dir.mkdir(parents=True)
    (project_root / "pyproject.toml").write_text(
        "[project]\nname = \"demo\"\n",
        encoding="utf-8",
    )
    (project_root / ".env").write_text(
        "OTHER=value\nDEEPSEEK_API_KEY='from-dotenv'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(llm_client, "__file__", str(moved_module_dir / "llm_client.py"))

    assert llm_client._load_dotenv_api_key() == "from-dotenv"


def test_load_dotenv_api_key_skips_when_project_root_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    moved_module_dir = tmp_path / "src" / "deep" / "nested" / "ai"
    moved_module_dir.mkdir(parents=True)
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=from-dotenv\n", encoding="utf-8")
    monkeypatch.setattr(llm_client, "__file__", str(moved_module_dir / "llm_client.py"))

    assert llm_client._load_dotenv_api_key() is None
