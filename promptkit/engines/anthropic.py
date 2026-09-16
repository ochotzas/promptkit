from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any, ClassVar

from promptkit.engines._sdk import require
from promptkit.engines.base import BaseEngine
from promptkit.errors import (
    AuthenticationError,
    ContextLengthError,
    EngineError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
)
from promptkit.retry import RetryPolicy
from promptkit.types import Capabilities, Chunk, Completion, Message, Usage, as_messages
from promptkit.utils.logging import get_logger

logger = get_logger(__name__)

EXTRA = "anthropic"
MODULE = "anthropic"
DEFAULT_MODEL = "claude-sonnet-4"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 60.0


def split_system(messages: list[Message]) -> tuple[str | None, list[Message]]:
    system = [m.content for m in messages if m.role == "system"]
    rest = [m for m in messages if m.role != "system"]

    return ("\n\n".join(system) or None, rest)


def build_params(
    messages: list[Message],
    model: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    system, conversation = split_system(messages)
    params: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens or DEFAULT_MAX_TOKENS,
        "messages": [{"role": m.role, "content": m.content} for m in conversation],
    }

    if system is not None:
        params["system"] = system

    if temperature is not None:
        params["temperature"] = temperature

    params.update({k: v for k, v in extra.items() if v is not None})

    return params


def parse_usage(raw: Any) -> Usage:
    usage = getattr(raw, "usage", None)

    if usage is None:
        return Usage(estimated=True)

    return Usage(
        prompt_tokens=int(getattr(usage, "input_tokens", 0) or 0),
        completion_tokens=int(getattr(usage, "output_tokens", 0) or 0),
    )


def parse_response(raw: Any, model: str) -> Completion:
    blocks = getattr(raw, "content", None) or []
    text = "".join(
        str(getattr(block, "text", ""))
        for block in blocks
        if getattr(block, "type", "text") == "text"
    )

    if not text:
        raise ProviderError("No text content in Anthropic API response", model=model)

    return Completion(
        text=text,
        model=str(getattr(raw, "model", model)),
        usage=parse_usage(raw),
        finish_reason=getattr(raw, "stop_reason", None),
        raw=raw,
    )


def parse_event(event: Any) -> Chunk | None:
    kind = getattr(event, "type", "")

    if kind == "content_block_delta":
        text = getattr(getattr(event, "delta", None), "text", None)

        if text:
            return Chunk(text=str(text), raw=event)

    if kind == "message_delta":
        stop = getattr(getattr(event, "delta", None), "stop_reason", None)

        if stop:
            return Chunk(text="", finish_reason=str(stop), raw=event)

    return None


def retry_after_of(error: Any) -> float | None:
    headers = getattr(getattr(error, "response", None), "headers", None)

    if headers is None:
        return None

    try:
        return float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


def map_error(error: Exception, model: str) -> EngineError:
    sdk = require(MODULE, EXTRA, "anthropic")
    message = str(getattr(error, "message", None) or error)

    if isinstance(error, sdk.AuthenticationError | sdk.PermissionDeniedError):
        return AuthenticationError(message, model=model)

    if isinstance(error, sdk.RateLimitError):
        return RateLimitError(message, model=model, retry_after=retry_after_of(error))

    if isinstance(error, sdk.NotFoundError):
        return ModelNotFoundError(message, model=model)

    if isinstance(error, sdk.BadRequestError):
        if "max_tokens" in message or "too long" in message.lower():
            return ContextLengthError(message, model=model)

        return ProviderError(message, model=model, status_code=400)

    if isinstance(error, sdk.APIStatusError):
        return ProviderError(
            message, model=model, status_code=getattr(error, "status_code", None)
        )

    if isinstance(error, sdk.APIConnectionError | sdk.APITimeoutError):
        return ProviderError(
            f"Could not reach the Anthropic API: {message}", model=model
        )

    if isinstance(error, sdk.APIError):
        return ProviderError(message, model=model)

    raise error


class AnthropicEngine(BaseEngine):
    capabilities: ClassVar[Capabilities] = Capabilities(
        streaming=True, json_mode=False, system_role=True
    )

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        temperature: float | None = None,
        max_tokens: int | None = DEFAULT_MAX_TOKENS,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry: RetryPolicy | None = None,
        **client_options: Any,
    ) -> None:
        super().__init__(model, retry)
        self.sdk = require(MODULE, EXTRA, type(self).__name__)
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.timeout = timeout
        self._options = client_options
        self._client: Any = None
        self._aclient: Any = None

    def _client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"timeout": self.timeout, "max_retries": 0}

        if self.api_key is not None:
            kwargs["api_key"] = self.api_key

        if self.base_url is not None:
            kwargs["base_url"] = self.base_url

        kwargs.update(self._options)

        return kwargs

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = self.sdk.Anthropic(**self._client_kwargs())

        return self._client

    @property
    def aclient(self) -> Any:
        if self._aclient is None:
            self._aclient = self.sdk.AsyncAnthropic(**self._client_kwargs())

        return self._aclient

    def _params(self, messages: list[Message], **options: Any) -> dict[str, Any]:
        options.pop("json_schema", None)

        return build_params(
            messages,
            options.pop("model", self.model),
            options.pop("temperature", self.temperature),
            options.pop("max_tokens", self.max_tokens),
            **options,
        )

    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        params = self._params(messages, **options)
        logger.debug(f"Calling Anthropic messages with model {self.model}")

        try:
            raw = self.client.messages.create(**params)
        except Exception as e:
            raise map_error(e, self.model) from e

        return parse_response(raw, self.model)

    async def _acomplete(self, messages: list[Message], **options: Any) -> Completion:
        params = self._params(messages, **options)
        logger.debug(f"Calling Anthropic messages async with model {self.model}")

        try:
            raw = await self.aclient.messages.create(**params)
        except Exception as e:
            raise map_error(e, self.model) from e

        return parse_response(raw, self.model)

    def stream(self, messages: str | list[Message], **options: Any) -> Iterator[Chunk]:
        params = self._params(as_messages(messages), **options)

        try:
            for event in self.client.messages.create(stream=True, **params):
                chunk = parse_event(event)

                if chunk is not None:
                    yield chunk
        except Exception as e:
            raise map_error(e, self.model) from e

    async def astream(
        self, messages: str | list[Message], **options: Any
    ) -> AsyncIterator[Chunk]:
        params = self._params(as_messages(messages), **options)

        try:
            events = await self.aclient.messages.create(stream=True, **params)

            async for event in events:
                chunk = parse_event(event)

                if chunk is not None:
                    yield chunk
        except Exception as e:
            raise map_error(e, self.model) from e

    def get_model_info(self) -> dict[str, Any]:
        return {
            **super().get_model_info(),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "base_url": self.base_url,
        }

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    async def aclose(self) -> None:
        self.close()

        if self._aclient is not None:
            await self._aclient.close()
            self._aclient = None
