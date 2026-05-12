from __future__ import annotations

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
