from __future__ import annotations

from typing import Any, ClassVar

from promptkit.engines.openai import OpenAIEngine
from promptkit.retry import RetryPolicy
from promptkit.types import Capabilities

KNOWN_ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "lmstudio": "http://localhost:1234/v1",
    "vllm": "http://localhost:8000/v1",
    "ollama": "http://localhost:11434/v1",
}


class CompatibleEngine(OpenAIEngine):
    capabilities: ClassVar[Capabilities] = Capabilities(
        streaming=True, json_mode=False, system_role=True
    )
    default_base_url: ClassVar[str | None] = None

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = "not-needed",
        temperature: float | None = 0.7,
        max_tokens: int | None = None,
        timeout: float = 60.0,
        retry: RetryPolicy | None = None,
        **client_options: Any,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=KNOWN_ENDPOINTS.get(base_url, base_url),
            timeout=timeout,
            retry=retry,
            **client_options,
        )


__all__ = ["KNOWN_ENDPOINTS", "CompatibleEngine"]
