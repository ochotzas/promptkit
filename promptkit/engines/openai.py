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
from promptkit.types import Capabilities, Chunk, Completion, Message, Usage
from promptkit.utils.logging import get_logger

logger = get_logger(__name__)

EXTRA = "openai"
MODULE = "openai"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT = 60.0


def build_params(
    messages: list[Message],
    model: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    json_schema: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "model": model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
    }

    if temperature is not None:
        params["temperature"] = temperature

    if max_tokens is not None:
        params["max_tokens"] = max_tokens

    if json_schema is not None:
        params["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "promptkit_output",
                "schema": json_schema,
                "strict": False,
            },
        }

    params.update({k: v for k, v in extra.items() if v is not None})

    return params


def parse_usage(raw: Any) -> Usage:
    usage = getattr(raw, "usage", None)

    if usage is None:
        return Usage(estimated=True)

    return Usage(
        prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
        completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
    )


def parse_response(raw: Any, model: str) -> Completion:
    choices = getattr(raw, "choices", None)

    if not choices:
        raise ProviderError("No choices returned from OpenAI API", model=model)

    choice = choices[0]
    content = getattr(choice.message, "content", None)

    if content is None:
        raise ProviderError("No content in OpenAI API response", model=model)

    return Completion(
        text=str(content),
        model=str(getattr(raw, "model", model)),
        usage=parse_usage(raw),
        finish_reason=getattr(choice, "finish_reason", None),
        raw=raw,
    )


def parse_chunk(raw: Any) -> Chunk | None:
    choices = getattr(raw, "choices", None)

    if not choices:
        return None

    choice = choices[0]
    text = getattr(choice.delta, "content", None)
    finish = getattr(choice, "finish_reason", None)

    if text is None and finish is None:
        return None

    return Chunk(text=text or "", finish_reason=finish, raw=raw)


def retry_after_of(error: Any) -> float | None:
    headers = getattr(getattr(error, "response", None), "headers", None)

    if headers is None:
        return None

    try:
        return float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


def map_error(error: Exception, model: str) -> EngineError:
    sdk = require(MODULE, EXTRA, "openai")
    message = str(getattr(error, "message", None) or error)

    if isinstance(error, sdk.AuthenticationError | sdk.PermissionDeniedError):
        return AuthenticationError(message, model=model)

    if isinstance(error, sdk.RateLimitError):
        return RateLimitError(message, model=model, retry_after=retry_after_of(error))

    if isinstance(error, sdk.NotFoundError):
        return ModelNotFoundError(message, model=model)

    if isinstance(error, sdk.BadRequestError):
        if "context" in message.lower() and "length" in message.lower():
            return ContextLengthError(message, model=model)

        return ProviderError(message, model=model, status_code=400)

    if isinstance(error, sdk.APIStatusError):
        return ProviderError(
            message, model=model, status_code=getattr(error, "status_code", None)
        )

    if isinstance(error, sdk.APIConnectionError | sdk.APITimeoutError):
        return ProviderError(f"Could not reach the OpenAI API: {message}", model=model)

    if isinstance(error, sdk.APIError):
        return ProviderError(message, model=model)

    raise error


class OpenAIEngine(BaseEngine):
    capabilities: ClassVar[Capabilities] = Capabilities(
        streaming=True, json_mode=True, system_role=True
    )
    extra: ClassVar[str] = EXTRA
    default_base_url: ClassVar[str | None] = None

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        temperature: float | None = 0.7,
        max_tokens: int | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry: RetryPolicy | None = None,
        **client_options: Any,
    ) -> None:
        super().__init__(model, retry)
        self.sdk = require(MODULE, self.extra, type(self).__name__)
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url or self.default_base_url
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
            self._client = self.sdk.OpenAI(**self._client_kwargs())

        return self._client

    @property
    def aclient(self) -> Any:
        if self._aclient is None:
            self._aclient = self.sdk.AsyncOpenAI(**self._client_kwargs())

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
        logger.debug(f"Calling OpenAI chat completions with model {self.model}")

        try:
            raw = self.client.chat.completions.create(**params)
        except Exception as e:
            raise map_error(e, self.model) from e

        return parse_response(raw, self.model)

    async def _acomplete(self, messages: list[Message], **options: Any) -> Completion:
        params = self._params(messages, **options)
        logger.debug(f"Calling OpenAI chat completions async with model {self.model}")

        try:
            raw = await self.aclient.chat.completions.create(**params)
        except Exception as e:
            raise map_error(e, self.model) from e

        return parse_response(raw, self.model)

    def stream(self, messages: str | list[Message], **options: Any) -> Iterator[Chunk]:
        from promptkit.types import as_messages

        params = self._params(as_messages(messages), **options)

        try:
            events = self.client.chat.completions.create(stream=True, **params)

            for raw in events:
                chunk = parse_chunk(raw)

                if chunk is not None:
                    yield chunk
        except Exception as e:
            raise map_error(e, self.model) from e

    async def astream(
        self, messages: str | list[Message], **options: Any
    ) -> AsyncIterator[Chunk]:
        from promptkit.types import as_messages

        params = self._params(as_messages(messages), **options)

        try:
            events = await self.aclient.chat.completions.create(stream=True, **params)

            async for raw in events:
                chunk = parse_chunk(raw)

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
