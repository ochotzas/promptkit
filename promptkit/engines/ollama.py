from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any, ClassVar

from promptkit.engines._sdk import require
from promptkit.engines.base import BaseEngine
from promptkit.errors import EngineError, ModelNotFoundError, ProviderError
from promptkit.retry import RetryPolicy
from promptkit.types import Capabilities, Chunk, Completion, Message, Usage, as_messages
from promptkit.utils.logging import get_logger

logger = get_logger(__name__)

EXTRA = "ollama"
MODULE = "ollama"
DEFAULT_MODEL = "llama3"
DEFAULT_HOST = "http://localhost:11434"


def build_params(
    messages: list[Message],
    model: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    json_schema: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    options: dict[str, Any] = {}

    if temperature is not None:
        options["temperature"] = temperature

    if max_tokens is not None:
        options["num_predict"] = max_tokens

    params: dict[str, Any] = {
        "model": model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
    }

    if options:
        params["options"] = options

    if json_schema is not None:
        params["format"] = json_schema

    params.update({k: v for k, v in extra.items() if v is not None})

    return params


def _field(raw: Any, name: str, default: Any = None) -> Any:
    if isinstance(raw, dict):
        return raw.get(name, default)

    return getattr(raw, name, default)


def parse_usage(raw: Any) -> Usage:
    prompt_tokens = _field(raw, "prompt_eval_count")
    completion_tokens = _field(raw, "eval_count")

    return Usage(
        prompt_tokens=int(prompt_tokens or 0),
        completion_tokens=int(completion_tokens or 0),
        estimated=prompt_tokens is None and completion_tokens is None,
    )


def parse_response(raw: Any, model: str) -> Completion:
    message = _field(raw, "message")
    content = _field(message, "content") if message is not None else None

    if content is None:
        content = _field(raw, "response")

    if content is None:
        raise ProviderError("No content in Ollama response", model=model)

    return Completion(
        text=str(content),
        model=str(_field(raw, "model", model)),
        usage=parse_usage(raw),
        finish_reason=_field(raw, "done_reason"),
        raw=raw,
    )


def parse_chunk(raw: Any) -> Chunk | None:
    message = _field(raw, "message")
    text = _field(message, "content") if message is not None else None
    done = bool(_field(raw, "done", False))

    if not text and not done:
        return None

    return Chunk(
        text=str(text or ""),
        finish_reason=_field(raw, "done_reason") if done else None,
        raw=raw,
    )


def map_error(error: Exception, model: str, host: str) -> EngineError:
    sdk = require(MODULE, EXTRA, "ollama")
    message = str(error)

    if isinstance(error, sdk.ResponseError):
        status = getattr(error, "status_code", None)

        if status == 404 or "not found" in message.lower():
            return ModelNotFoundError(
                f"Model '{model}' not found. Install it with: ollama pull {model}",
                model=model,
            )

        return ProviderError(message, model=model, status_code=status)

    if isinstance(error, ConnectionError | OSError):
        return ProviderError(
            f"Cannot connect to Ollama at {host}. Is it running?", model=model
        )

    return ProviderError(message, model=model)


class OllamaEngine(BaseEngine):
    capabilities: ClassVar[Capabilities] = Capabilities(
        streaming=True, json_mode=True, system_role=True
    )

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST,
        temperature: float | None = 0.7,
        max_tokens: int | None = None,
        timeout: float = 300.0,
        retry: RetryPolicy | None = None,
        **client_options: Any,
    ) -> None:
        super().__init__(model, retry)
        self.sdk = require(MODULE, EXTRA, type(self).__name__)
        self.host = host.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._options = client_options
        self._client: Any = None
        self._aclient: Any = None

    @property
    def base_url(self) -> str:
        return self.host

    def _client_kwargs(self) -> dict[str, Any]:
        return {"host": self.host, "timeout": self.timeout, **self._options}

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = self.sdk.Client(**self._client_kwargs())

        return self._client

    @property
    def aclient(self) -> Any:
        if self._aclient is None:
            self._aclient = self.sdk.AsyncClient(**self._client_kwargs())

        return self._aclient

    def _params(self, messages: list[Message], **options: Any) -> dict[str, Any]:
        return build_params(
            messages,
            options.pop("model", self.model),
            options.pop("temperature", self.temperature),
            options.pop("max_tokens", self.max_tokens),
            options.pop("json_schema", None),
            **options,
        )

    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        params = self._params(messages, **options)
        logger.debug(f"Calling Ollama chat with model {self.model}")

        try:
            raw = self.client.chat(**params)
        except Exception as e:
            raise map_error(e, self.model, self.host) from e

        return parse_response(raw, self.model)

    async def _acomplete(self, messages: list[Message], **options: Any) -> Completion:
        params = self._params(messages, **options)
        logger.debug(f"Calling Ollama chat async with model {self.model}")

        try:
            raw = await self.aclient.chat(**params)
        except Exception as e:
            raise map_error(e, self.model, self.host) from e

        return parse_response(raw, self.model)

    def stream(self, messages: str | list[Message], **options: Any) -> Iterator[Chunk]:
        params = self._params(as_messages(messages), **options)

        try:
            for raw in self.client.chat(stream=True, **params):
                chunk = parse_chunk(raw)

                if chunk is not None:
                    yield chunk
        except Exception as e:
            raise map_error(e, self.model, self.host) from e

    async def astream(
        self, messages: str | list[Message], **options: Any
    ) -> AsyncIterator[Chunk]:
        params = self._params(as_messages(messages), **options)

        try:
            events = await self.aclient.chat(stream=True, **params)

            async for raw in events:
                chunk = parse_chunk(raw)

                if chunk is not None:
                    yield chunk
        except Exception as e:
            raise map_error(e, self.model, self.host) from e

    def list_models(self) -> list[str]:
        try:
            listing = self.client.list()
        except Exception as e:
            raise map_error(e, self.model, self.host) from e

        models = _field(listing, "models") or []

        return [str(_field(m, "model") or _field(m, "name")) for m in models]

    def get_model_info(self) -> dict[str, Any]:
        return {
            **super().get_model_info(),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "base_url": self.host,
        }

    def close(self) -> None:
        self._client = None

    async def aclose(self) -> None:
        self.close()
        self._aclient = None
