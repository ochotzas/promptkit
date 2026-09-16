from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from promptkit.types import Message, Role

VALID_ROLES = ("system", "user", "assistant")


class MessageTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Role = Field(default="user")
    template: str = Field(...)

    @field_validator("role", mode="before")
    @classmethod
    def _known_role(cls, value: Any) -> Any:
        if isinstance(value, str) and value not in VALID_ROLES:
            raise ValueError(
                f"unknown role '{value}'; expected one of {', '.join(VALID_ROLES)}"
            )

        return value


def from_legacy_template(template: str) -> tuple[MessageTemplate, ...]:
    return (MessageTemplate(role="user", template=template),)


def parse_messages(raw: Any) -> tuple[MessageTemplate, ...]:
    if isinstance(raw, str):
        return from_legacy_template(raw)

    if isinstance(raw, MessageTemplate):
        return (raw,)

    if not isinstance(raw, list | tuple):
        raise TypeError(f"messages must be a list, got {type(raw).__name__}")

    parsed: list[MessageTemplate] = []

    for entry in raw:
        if isinstance(entry, MessageTemplate):
            parsed.append(entry)
        elif isinstance(entry, str):
            parsed.append(MessageTemplate(role="user", template=entry))
        elif isinstance(entry, dict):
            parsed.append(_from_mapping(entry))
        else:
            raise TypeError(
                f"each message must be a string or mapping, got {type(entry).__name__}"
            )

    return tuple(parsed)


def _from_mapping(entry: dict[str, Any]) -> MessageTemplate:
    for role in VALID_ROLES:
        if role in entry and len(entry) == 1:
            return MessageTemplate.model_validate(
                {"role": role, "template": entry[role]}
            )

    return MessageTemplate.model_validate(
        {
            "role": entry.get("role", "user"),
            "template": entry.get("template", entry.get("content", "")),
        }
    )


def to_messages(
    templates: tuple[MessageTemplate, ...], rendered: list[str]
) -> list[Message]:
    return [
        Message(role=template.role, content=text)
        for template, text in zip(templates, rendered, strict=True)
        if text.strip()
    ]


__all__ = [
    "VALID_ROLES",
    "MessageTemplate",
    "from_legacy_template",
    "parse_messages",
    "to_messages",
]
