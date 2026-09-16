from __future__ import annotations

import asyncio
from typing import Any

import pytest

from promptkit.cache import MemoryCache
from promptkit.core.prompt import Prompt
from promptkit.core.runner import (
    run_prompt,
    run_prompt_async,
    run_prompt_text,
    run_prompt_text_async,
)
from promptkit.engines.base import BaseEngine
from promptkit.errors import InputValidationError, ProviderError
from promptkit.events import Recorder
from promptkit.retry import NO_RETRY
from promptkit.types import Completion, Message, Usage


class Async(BaseEngine):
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        super().__init__(model)
        self.sync_calls = 0
        self.async_calls = 0

    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        self.sync_calls += 1

        return Completion(text="sync", model=self.model, usage=Usage(4, 2))

    async def _acomplete(self, messages: list[Message], **options: Any) -> Completion:
        self.async_calls += 1

        return Completion(text="async", model=self.model, usage=Usage(6, 3))


class Failing(BaseEngine):
    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        raise ProviderError("upstream down", model=self.model, status_code=400)


class OptionCapture(BaseEngine):
    def __init__(self) -> None:
        super().__init__("m")
        self.options: dict[str, Any] = {}

    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        self.options = options

        return Completion(text="", model=self.model)


@pytest.fixture
def prompt() -> Prompt:
    return Prompt(
        name="greet", description="d", template="Hi {{ n }}", input_schema={"n": "str"}
    )


class TestSync:
    def test_returns_completion(self, prompt: Prompt) -> None:
        result = run_prompt(prompt, {"n": "A"}, Async())

        assert isinstance(result, Completion)
        assert result.text == "sync"
        assert result.usage == Usage(4, 2)

    def test_str_gives_text_back(self, prompt: Prompt) -> None:
        assert str(run_prompt(prompt, {"n": "A"}, Async())) == "sync"

    def test_text_helper_returns_str(self, prompt: Prompt) -> None:
        result = run_prompt_text(prompt, {"n": "A"}, Async())

        assert isinstance(result, str)
        assert result == "sync"

    def test_validation_error_propagates(self, prompt: Prompt) -> None:
        with pytest.raises(InputValidationError):
            run_prompt(prompt, {}, Async())

    def test_validation_can_be_skipped(self, prompt: Prompt) -> None:
        result = run_prompt(prompt, {"n": "A"}, Async(), validate_inputs=False)

        assert result.text == "sync"

    def test_engine_error_propagates(self, prompt: Prompt) -> None:
        with pytest.raises(ProviderError, match="upstream down"):
            run_prompt(prompt, {"n": "A"}, Failing("m", retry=NO_RETRY))

    def test_options_reach_the_engine(self, prompt: Prompt) -> None:
        engine = OptionCapture()
        run_prompt(prompt, {"n": "A"}, engine, temperature=0.1, top_p=0.5)

        assert engine.options == {"temperature": 0.1, "top_p": 0.5}


class TestAsync:
    def test_uses_the_async_path(self, prompt: Prompt) -> None:
        engine = Async()
        result = asyncio.run(run_prompt_async(prompt, {"n": "A"}, engine))

        assert result.text == "async"
        assert engine.async_calls == 1
        assert engine.sync_calls == 0

    def test_returns_completion(self, prompt: Prompt) -> None:
        result = asyncio.run(run_prompt_async(prompt, {"n": "A"}, Async()))

        assert isinstance(result, Completion)
        assert result.usage == Usage(6, 3)

    def test_text_helper_returns_str(self, prompt: Prompt) -> None:
        result = asyncio.run(run_prompt_text_async(prompt, {"n": "A"}, Async()))

        assert isinstance(result, str)
        assert result == "async"

    def test_validation_error_propagates(self, prompt: Prompt) -> None:
        with pytest.raises(InputValidationError):
            asyncio.run(run_prompt_async(prompt, {}, Async()))

    def test_engine_error_propagates(self, prompt: Prompt) -> None:
        with pytest.raises(ProviderError):
            asyncio.run(
                run_prompt_async(prompt, {"n": "A"}, Failing("m", retry=NO_RETRY))
            )

    def test_cache_is_shared_with_sync(self, prompt: Prompt) -> None:
        cache = MemoryCache()
        engine = Async()
        run_prompt(prompt, {"n": "A"}, engine, cache=cache)
        result = asyncio.run(run_prompt_async(prompt, {"n": "A"}, engine, cache=cache))

        assert result.text == "sync"
        assert engine.async_calls == 0

    def test_async_cache_miss_then_hit(self, prompt: Prompt) -> None:
        async def go() -> int:
            cache = MemoryCache()
            engine = Async()
            await run_prompt_async(prompt, {"n": "A"}, engine, cache=cache)
            await run_prompt_async(prompt, {"n": "A"}, engine, cache=cache)

            return engine.async_calls

        assert asyncio.run(go()) == 1

    def test_emits_events(self, prompt: Prompt) -> None:
        recorder = Recorder()
        asyncio.run(run_prompt_async(prompt, {"n": "A"}, Async(), listeners=[recorder]))

        assert [type(e).__name__ for e in recorder.events] == [
            "PromptRendered",
            "RequestStarted",
            "RequestCompleted",
        ]

    def test_concurrent_runs(self, prompt: Prompt) -> None:
        async def go() -> list[Completion]:
            engine = Async()

            return await asyncio.gather(
                *(run_prompt_async(prompt, {"n": str(i)}, engine) for i in range(5))
            )

        results = asyncio.run(go())

        assert len(results) == 5
        assert all(r.text == "async" for r in results)
