from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest

from promptkit import events
from promptkit.core.prompt import Prompt
from promptkit.core.runner import run_prompt
from promptkit.engines.base import BaseEngine
from promptkit.errors import ProviderError
from promptkit.events import listening
from promptkit.retry import NO_RETRY
from promptkit.telemetry.otel import OpenTelemetryListener, attributes
from promptkit.types import Completion, Message, Usage

pytest.importorskip("opentelemetry.sdk")


class Ok(BaseEngine):
    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        return Completion(text="hi", model=self.model, usage=Usage(11, 4))


class Boom(BaseEngine):
    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        raise ProviderError("upstream down", model=self.model, status_code=500)


@pytest.fixture(autouse=True)
def _isolate() -> Iterator[None]:
    events.clear_listeners()
    yield
    events.clear_listeners()


@dataclass(slots=True)
class Recorded:
    exporter: Any
    tracer: Any

    def get_finished_spans(self) -> Any:
        return self.exporter.get_finished_spans()


@pytest.fixture
def exporter() -> Recorded:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    memory = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(memory))

    return Recorded(exporter=memory, tracer=provider.get_tracer("test"))


@pytest.fixture
def prompt() -> Prompt:
    return Prompt(
        name="greet", description="d", template="Hi {{ n }}", input_schema={"n": "str"}
    )


class TestSpans:
    def test_success_creates_a_span(self, exporter: Recorded, prompt: Prompt) -> None:
        with listening(OpenTelemetryListener(exporter.tracer)):
            run_prompt(prompt, {"n": "A"}, Ok("gpt-4o-mini"))

        spans = exporter.get_finished_spans()

        assert [s.name for s in spans] == ["promptkit.run"]

    def test_attributes_follow_gen_ai_conventions(
        self, exporter: Recorded, prompt: Prompt
    ) -> None:
        with listening(OpenTelemetryListener(exporter.tracer)):
            run_prompt(prompt, {"n": "A"}, Ok("gpt-4o-mini"))

        attrs = dict(exporter.get_finished_spans()[0].attributes)

        assert attrs["gen_ai.request.model"] == "gpt-4o-mini"
        assert attrs["gen_ai.usage.input_tokens"] == 11
        assert attrs["gen_ai.usage.output_tokens"] == 4
        assert attrs["promptkit.prompt.name"] == "greet"
        assert attrs["promptkit.usage.estimated"] is False

    def test_cost_is_recorded_when_known(
        self, exporter: Recorded, prompt: Prompt
    ) -> None:
        with listening(OpenTelemetryListener(exporter.tracer)):
            run_prompt(prompt, {"n": "A"}, Ok("gpt-4o-mini"))

        assert "promptkit.cost_usd" in dict(exporter.get_finished_spans()[0].attributes)

    def test_failure_sets_error_status(
        self, exporter: Recorded, prompt: Prompt
    ) -> None:
        from opentelemetry.trace import StatusCode

        with (
            listening(OpenTelemetryListener(exporter.tracer)),
            pytest.raises(ProviderError),
        ):
            run_prompt(prompt, {"n": "A"}, Boom("m", retry=NO_RETRY))

        span = exporter.get_finished_spans()[0]

        assert span.status.status_code is StatusCode.ERROR
        assert dict(span.attributes)["promptkit.error.type"] == "ProviderError"


class TestPrivacy:
    def test_no_prompt_content_by_default(
        self, exporter: Recorded, prompt: Prompt
    ) -> None:
        with listening(OpenTelemetryListener(exporter.tracer)):
            run_prompt(prompt, {"n": "SECRET-VALUE"}, Ok("gpt-4o-mini"))

        rendered = str(dict(exporter.get_finished_spans()[0].attributes))

        assert "SECRET-VALUE" not in rendered

    def test_error_text_is_withheld_by_default(self, prompt: Prompt) -> None:
        from promptkit.events import RequestFailed

        event = RequestFailed(
            prompt_name="p",
            model="m",
            error="secret detail",
            error_type="ProviderError",
        )

        assert "promptkit.error.message" not in attributes(event)

    def test_error_text_is_included_when_opted_in(self) -> None:
        from promptkit.events import RequestFailed

        event = RequestFailed(
            prompt_name="p",
            model="m",
            error="secret detail",
            error_type="ProviderError",
        )
        attrs = attributes(event, include_content=True)

        assert attrs["promptkit.error.message"] == "secret detail"


class TestInstall:
    def test_install_and_uninstall(self, exporter: Recorded) -> None:
        from promptkit.telemetry import install, uninstall

        listener = install(exporter.tracer)

        assert events.listener_count() == 1

        uninstall(listener)

        assert events.listener_count() == 0

    def test_a_broken_tracer_cannot_break_a_run(self, prompt: Prompt) -> None:
        class Exploding:
            def start_span(self, name: str) -> Any:
                raise RuntimeError("tracer down")

        with listening(OpenTelemetryListener(Exploding())):
            assert run_prompt(prompt, {"n": "A"}, Ok("m")).text == "hi"
