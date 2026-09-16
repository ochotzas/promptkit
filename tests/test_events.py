from __future__ import annotations

from collections.abc import Iterator

import pytest

from promptkit import events
from promptkit.cache import MemoryCache
from promptkit.core.prompt import Prompt
from promptkit.core.runner import run_prompt
from promptkit.engines.base import BaseEngine
from promptkit.errors import InputValidationError, RateLimitError
from promptkit.events import (
    PromptRendered,
    Recorder,
    RequestCompleted,
    RequestFailed,
    RequestStarted,
    listening,
)
from promptkit.retry import NO_RETRY
from promptkit.types import Completion, Message, Usage


class Ok(BaseEngine):
    def _complete(self, messages: list[Message], **options: object) -> Completion:
        return Completion(text="response", model=self.model, usage=Usage(10, 5))


class Boom(BaseEngine):
    def _complete(self, messages: list[Message], **options: object) -> Completion:
        raise RateLimitError("too fast", model=self.model)


@pytest.fixture(autouse=True)
def _isolate() -> Iterator[None]:
    events.clear_listeners()
    yield
    events.clear_listeners()


@pytest.fixture
def prompt() -> Prompt:
    return Prompt(
        name="greet", description="d", template="Hi {{ n }}", input_schema={"n": "str"}
    )


class TestRegistration:
    def test_subscribe_and_unsubscribe(self) -> None:
        recorder = Recorder()
        events.subscribe(recorder)

        assert events.listener_count() == 1

        events.unsubscribe(recorder)

        assert events.listener_count() == 0

    def test_unsubscribe_unknown_listener_is_safe(self) -> None:
        events.unsubscribe(Recorder())

    def test_listening_context_manager_cleans_up(self) -> None:
        with listening(Recorder()):
            assert events.listener_count() == 1

        assert events.listener_count() == 0

    def test_listener_cannot_break_the_run(self, prompt: Prompt) -> None:
        def explode(event: events.Event) -> None:
            raise RuntimeError("listener blew up")

        with listening(explode):
            assert run_prompt(prompt, {"n": "A"}, Ok("m")).text == "response"


class TestLifecycleEvents:
    def test_successful_run_emits_in_order(self, prompt: Prompt) -> None:
        recorder = Recorder()

        with listening(recorder):
            run_prompt(prompt, {"n": "A"}, Ok("gpt-4o-mini"))

        assert [type(e).__name__ for e in recorder.events] == [
            "PromptRendered",
            "RequestStarted",
            "RequestCompleted",
        ]

    def test_rendered_event_carries_size(self, prompt: Prompt) -> None:
        recorder = Recorder()

        with listening(recorder):
            run_prompt(prompt, {"n": "Alice"}, Ok("m"))

        rendered = recorder.of(PromptRendered)[0]

        assert rendered.prompt_name == "greet"
        assert rendered.characters == len("Hi Alice")
        assert rendered.message_count == 1

    def test_completed_event_carries_usage_and_cost(self, prompt: Prompt) -> None:
        recorder = Recorder()

        with listening(recorder):
            run_prompt(prompt, {"n": "A"}, Ok("gpt-4o-mini"))

        completed = recorder.of(RequestCompleted)[0]

        assert completed.usage == Usage(10, 5)
        assert completed.cost is not None
        assert completed.duration_seconds >= 0.0
        assert completed.engine == "Ok"

    def test_failure_emits_request_failed(self, prompt: Prompt) -> None:
        recorder = Recorder()

        with listening(recorder), pytest.raises(RateLimitError):
            run_prompt(prompt, {"n": "A"}, Boom("m", retry=NO_RETRY))

        failed = recorder.of(RequestFailed)[0]

        assert failed.error_type == "RateLimitError"
        assert "too fast" in failed.error

    def test_validation_failure_emits_failed_without_started(
        self, prompt: Prompt
    ) -> None:
        recorder = Recorder()

        with listening(recorder), pytest.raises(InputValidationError):
            run_prompt(prompt, {}, Ok("m"))

        assert recorder.of(RequestStarted) == []
        assert len(recorder.of(RequestFailed)) == 1

    def test_cached_run_is_flagged(self, prompt: Prompt) -> None:
        cache = MemoryCache()
        engine = Ok("m")
        run_prompt(prompt, {"n": "A"}, engine, cache=cache)

        recorder = Recorder()

        with listening(recorder):
            run_prompt(prompt, {"n": "A"}, engine, cache=cache)

        assert recorder.of(RequestCompleted)[0].cached is True
        assert recorder.of(RequestStarted) == []


class TestScopedListeners:
    def test_per_call_listener_receives_events(self, prompt: Prompt) -> None:
        recorder = Recorder()
        run_prompt(prompt, {"n": "A"}, Ok("m"), listeners=[recorder])

        assert len(recorder.events) == 3

    def test_per_call_listener_is_not_registered_globally(self, prompt: Prompt) -> None:
        run_prompt(prompt, {"n": "A"}, Ok("m"), listeners=[Recorder()])

        assert events.listener_count() == 0

    def test_no_listeners_is_fine(self, prompt: Prompt) -> None:
        assert run_prompt(prompt, {"n": "A"}, Ok("m")).text == "response"
