from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated: bool = False

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True, slots=True)
class Completion:
    text: str
    model: str
    usage: Usage = field(default_factory=Usage)
    finish_reason: str | None = None
    raw: Any = None

    def __str__(self) -> str:
        return self.text

    def __len__(self) -> int:
        return len(self.text)


@dataclass(frozen=True, slots=True)
class Chunk:
    text: str
    finish_reason: str | None = None
    raw: Any = None

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True, slots=True)
class Capabilities:
    streaming: bool = False
    json_mode: bool = False
    system_role: bool = True


def as_messages(prompt: str | list[Message]) -> list[Message]:
    if isinstance(prompt, str):
        return [Message(role="user", content=prompt)]

    return list(prompt)


def flatten(messages: list[Message], system_role: bool = True) -> str:
    if system_role:
        return "\n\n".join(m.content for m in messages)

    system = [m.content for m in messages if m.role == "system"]
    rest = [m.content for m in messages if m.role != "system"]

    return "\n\n".join(system + rest)


__all__ = [
    "Capabilities",
    "Chunk",
    "Completion",
    "Message",
    "Role",
    "Usage",
    "as_messages",
    "flatten",
]
