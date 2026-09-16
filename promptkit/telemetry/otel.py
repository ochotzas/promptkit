from __future__ import annotations

from typing import Any

from promptkit.engines._sdk import require
from promptkit.events import (
    Event,
    Listener,
    ParseRetried,
    RequestCompleted,
    RequestFailed,
    subscribe,
    unsubscribe,
)

EXTRA = "otel"
MODULE = "opentelemetry"
SCOPE = "promptkit"


def _tracer(name: str = SCOPE) -> Any:
    trace = require("opentelemetry.trace", EXTRA, "OpenTelemetry")

    return trace.get_tracer(name)


def attributes(event: Event, include_content: bool = False) -> dict[str, Any]:
    values: dict[str, Any] = {
        "promptkit.prompt.name": event.prompt_name,
        "gen_ai.request.model": event.model,
    }

    if isinstance(event, RequestCompleted):
        values["gen_ai.usage.input_tokens"] = event.usage.prompt_tokens
        values["gen_ai.usage.output_tokens"] = event.usage.completion_tokens
        values["promptkit.usage.estimated"] = event.usage.estimated
        values["promptkit.duration_seconds"] = round(event.duration_seconds, 6)
        values["promptkit.cached"] = event.cached
        values["promptkit.engine"] = event.engine

        if event.cost is not None:
            values["promptkit.cost_usd"] = event.cost

    if isinstance(event, RequestFailed):
        values["promptkit.error.type"] = event.error_type
        values["promptkit.engine"] = event.engine
        values["promptkit.duration_seconds"] = round(event.duration_seconds, 6)

        if include_content:
            values["promptkit.error.message"] = event.error

    if isinstance(event, ParseRetried):
        values["promptkit.parse.attempt"] = event.attempt

    return values


class OpenTelemetryListener:
    def __init__(
        self, tracer: Any = None, include_content: bool = False, scope: str = SCOPE
    ) -> None:
        self.tracer = tracer if tracer is not None else _tracer(scope)
        self.include_content = include_content

    def __call__(self, event: Event) -> None:
        if isinstance(event, RequestCompleted):
            self._record("promptkit.run", event, ok=True)
        elif isinstance(event, RequestFailed):
            self._record("promptkit.run", event, ok=False)
        elif isinstance(event, ParseRetried):
            self._record("promptkit.parse_retry", event, ok=False)

    def _record(self, name: str, event: Event, ok: bool) -> None:
        span = self.tracer.start_span(name)

        try:
            for key, value in attributes(event, self.include_content).items():
                span.set_attribute(key, value)

            if not ok:
                from opentelemetry.trace import Status, StatusCode

                span.set_status(Status(StatusCode.ERROR))
        finally:
            span.end()


def install(tracer: Any = None, include_content: bool = False) -> Listener:
    return subscribe(OpenTelemetryListener(tracer, include_content))


def uninstall(listener: Listener) -> None:
    unsubscribe(listener)


__all__ = [
    "EXTRA",
    "OpenTelemetryListener",
    "attributes",
    "install",
    "uninstall",
]
