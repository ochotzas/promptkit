from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from typing import Any

from promptkit.types import Usage


@dataclass(frozen=True, slots=True)
class Event:
    prompt_name: str
    model: str


@dataclass(frozen=True, slots=True)
class PromptRendered(Event):
    characters: int = 0
    message_count: int = 0


@dataclass(frozen=True, slots=True)
class RequestStarted(Event):
    engine: str = ""
    attempt: int = 1
    cached: bool = False


@dataclass(frozen=True, slots=True)
class RequestCompleted(Event):
    engine: str = ""
    usage: Usage = field(default_factory=Usage)
    duration_seconds: float = 0.0
    cost: float | None = None
    cost_exact: bool = True
    cached: bool = False


@dataclass(frozen=True, slots=True)
class RequestFailed(Event):
    engine: str = ""
    error: str = ""
    error_type: str = ""
    attempt: int = 1
    duration_seconds: float = 0.0
    will_retry: bool = False


@dataclass(frozen=True, slots=True)
class ParseRetried(Event):
    attempt: int = 1
    error: str = ""


Listener = Callable[[Event], None]

_listeners: list[Listener] = []


def subscribe(listener: Listener) -> Listener:
    _listeners.append(listener)

    return listener


def unsubscribe(listener: Listener) -> None:
    if listener in _listeners:
        _listeners.remove(listener)


def clear_listeners() -> None:
    _listeners.clear()


def listener_count() -> int:
    return len(_listeners)


@contextmanager
def listening(listener: Listener) -> Iterator[Listener]:
    subscribe(listener)
    try:
        yield listener
    finally:
        unsubscribe(listener)


def emit(event: Event, extra: list[Listener] | None = None) -> None:
    for listener in (*_listeners, *(extra or ())):
        with suppress(Exception):
            listener(event)


class Recorder:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def __call__(self, event: Event) -> None:
        self.events.append(event)

    def of(self, kind: type[Event]) -> list[Any]:
        return [e for e in self.events if isinstance(e, kind)]


__all__ = [
    "Event",
    "Listener",
    "ParseRetried",
    "PromptRendered",
    "Recorder",
    "RequestCompleted",
    "RequestFailed",
    "RequestStarted",
    "clear_listeners",
    "emit",
    "listener_count",
    "listening",
    "subscribe",
    "unsubscribe",
]
