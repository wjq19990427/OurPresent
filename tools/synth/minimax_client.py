"""Small Minimax client used only by the synthetic data tool."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class MinimaxConfigError(ValueError):
    """Raised when the synth-only Minimax environment is invalid."""


class MinimaxClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 60,
    ) -> None:
        load_dotenv_if_present()
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.base_url = (base_url or os.getenv("MINIMAX_BASE_URL", "")).rstrip("/")
        self.model = model or os.getenv("MINIMAX_MODEL", "")
        self.timeout = timeout
        self._validate()

    def generate_json(self, prompt: str) -> dict[str, Any]:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "response_format": {"type": "json_object"},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Minimax request failed: {exc}") from exc

        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, dict):
            return content
        return json.loads(content)

    def _validate(self) -> None:
        if not self.api_key:
            raise MinimaxConfigError("MINIMAX_API_KEY is required")
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https":
            raise MinimaxConfigError("MINIMAX_BASE_URL must use https")
        if not self.model:
            raise MinimaxConfigError("MINIMAX_MODEL is required")


def load_dotenv_if_present(path: Path | None = None) -> None:
    env_path = path or Path.cwd() / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
