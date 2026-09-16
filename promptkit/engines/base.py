from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import Any, ClassVar, TypeVar

from promptkit.errors import EngineError
from promptkit.pricing import estimate_cost, lookup
from promptkit.retry import RetryPolicy, retry_after_of
from promptkit.types import (
    Capabilities,
    Chunk,
    Completion,
    Message,
    Usage,
    as_messages,
    flatten,
)
from promptkit.utils.tokens import estimate_tokens

EngineT = TypeVar("EngineT", bound="BaseEngine")

__all__ = ["BaseEngine", "EngineError"]


class BaseEngine(ABC):
    capabilities: ClassVar[Capabilities] = Capabilities()

    def __init__(
        self, model: str = "default", retry: RetryPolicy | None = None
    ) -> None:
        self.model = model
        self.retry = retry if retry is not None else RetryPolicy()

    @abstractmethod
    def _complete(self, messages: list[Message], **options: Any) -> Completion: ...

    async def _acomplete(self, messages: list[Message], **options: Any) -> Completion:
        return self._complete(messages, **options)

    def _as_completion(self, text: str, messages: list[Message]) -> Completion:
        return Completion(
            text=text,
            model=self.model,
            usage=Usage(
                prompt_tokens=estimate_tokens(flatten(messages)),
                completion_tokens=estimate_tokens(text),
                estimated=True,
            ),
        )

    def complete(self, messages: str | list[Message], **options: Any) -> Completion:
        resolved = as_messages(messages)

        return self._retrying(lambda: self._complete(resolved, **options))

    async def acomplete(
        self, messages: str | list[Message], **options: Any
    ) -> Completion:
        resolved = as_messages(messages)

        return await self._aretrying(lambda: self._acomplete(resolved, **options))

    def _retrying(self, call: Callable[[], Completion]) -> Completion:
        attempt = 1

        while True:
            try:
                return call()
            except Exception as e:
                if not self.retry.should_retry(e, attempt):
                    raise

                time.sleep(self.retry.backoff(attempt, retry_after_of(e)))
                attempt += 1

    async def _aretrying(self, call: Callable[[], Awaitable[Completion]]) -> Completion:
        attempt = 1

        while True:
            try:
                return await call()
            except Exception as e:
                if not self.retry.should_retry(e, attempt):
                    raise

                await asyncio.sleep(self.retry.backoff(attempt, retry_after_of(e)))
                attempt += 1

    def generate(self, prompt: str) -> str:
        return self.complete(prompt).text

    async def generate_async(self, prompt: str) -> str:
        return (await self.acomplete(prompt)).text

    def stream(self, messages: str | list[Message], **options: Any) -> Iterator[Chunk]:
        raise NotImplementedError(f"{type(self).__name__} does not support streaming")

    def astream(
        self, messages: str | list[Message], **options: Any
    ) -> AsyncIterator[Chunk]:
        raise NotImplementedError(f"{type(self).__name__} does not support streaming")

    def get_model_info(self) -> dict[str, Any]:
        return {
            "engine": type(self).__name__,
            "model": self.model,
            "capabilities": {
                "streaming": self.capabilities.streaming,
                "json_mode": self.capabilities.json_mode,
                "system_role": self.capabilities.system_role,
            },
        }

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float | None:
        return estimate_cost(input_tokens, output_tokens, self.model)

    def cost_of(self, completion: Completion) -> float | None:
        return estimate_cost(
            completion.usage.prompt_tokens,
            completion.usage.completion_tokens,
            completion.model,
        )

    def pricing_is_exact(self, completion: Completion) -> bool:
        found = lookup(completion.model)

        return found.exact if found is not None else False

    def close(self) -> None:
        return None

    async def aclose(self) -> None:
        self.close()

    def __enter__(self: EngineT) -> EngineT:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    async def __aenter__(self: EngineT) -> EngineT:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
