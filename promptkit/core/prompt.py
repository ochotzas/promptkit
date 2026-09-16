from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from promptkit.core.compiler import compiler_for
from promptkit.core.message import MessageTemplate, parse_messages
from promptkit.core.schema import compile_input_schema, is_optional, validate_inputs
from promptkit.errors import PromptParseError
from promptkit.types import Message

DEFAULT_VERSION = "0.1.0"


class PromptMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    tags: tuple[str, ...] = ()
    author: str | None = None
    model: str | None = None
    temperature: float | None = None


class Prompt(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(...)
    description: str = Field(...)
    version: str = Field(default=DEFAULT_VERSION)
    messages: tuple[MessageTemplate, ...] = Field(default=())
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] | None = Field(default=None)
    metadata: PromptMetadata = Field(default_factory=PromptMetadata)
    dependencies: tuple[tuple[str, str], ...] = Field(default=())
    template_root: str | None = Field(default=None)

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            name: str,
            description: str,
            version: str = DEFAULT_VERSION,
            template: str = ...,
            messages: Any = ...,
            input_schema: dict[str, Any] = ...,
            output_schema: dict[str, Any] | None = ...,
            metadata: Any = ...,
            dependencies: Any = ...,
            template_root: str | None = ...,
        ) -> None: ...

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_template(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        legacy = payload.pop("template", None)

        if payload.get("messages"):
            payload["messages"] = parse_messages(payload["messages"])
        elif legacy is not None:
            payload["messages"] = parse_messages(legacy)

        return payload

    @model_validator(mode="after")
    def _require_content(self) -> Prompt:
        if not self.messages:
            raise ValueError("a prompt needs at least one message or a template")

        return self

    @property
    def joined_template(self) -> str:
        return "\n\n".join(m.template for m in self.messages)

    @property
    def fingerprint(self) -> str:
        payload = {
            "messages": [[m.role, m.template] for m in self.messages],
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "dependencies": sorted(self.dependencies),
        }
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        )

        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def validate_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return validate_inputs(inputs, self.input_schema)

    def render_messages(
        self, inputs: dict[str, Any], validate: bool = True
    ) -> list[Message]:
        if validate:
            inputs = self.validate_inputs(inputs)

        compiler = compiler_for(self.template_root)
        rendered = []

        for message in self.messages:
            text = compiler.render_string(message.template, inputs)

            if text.strip():
                rendered.append(Message(role=message.role, content=text))

        return rendered

    def render(self, inputs: dict[str, Any], validate: bool = True) -> str:
        return "\n\n".join(m.content for m in self.render_messages(inputs, validate))

    def output_model(self, name: str | None = None) -> type[BaseModel] | None:
        if self.output_schema is None:
            return None

        from promptkit.core.jsonschema import compile_json_schema

        return compile_json_schema(self.output_schema, name or f"{self.name}_output")

    def input_model(self) -> type[BaseModel] | None:
        return compile_input_schema(self.input_schema)

    def get_required_inputs(self) -> list[str]:
        return [f for f, optional in self._fields() if not optional]

    def get_optional_inputs(self) -> list[str]:
        return [f for f, optional in self._fields() if optional]

    def _fields(self) -> list[tuple[str, bool]]:
        from promptkit.core.jsonschema import looks_like_json_schema

        if looks_like_json_schema(self.input_schema):
            properties = self.input_schema.get("properties") or {}
            required = set(self.input_schema.get("required") or ())

            return [(f, f not in required) for f in properties]

        return [
            (field, is_optional(str(type_str)))
            for field, type_str in self.input_schema.items()
        ]

    def with_dependencies(self, dependencies: dict[str, str]) -> Prompt:
        return self.model_copy(
            update={"dependencies": tuple(sorted(dependencies.items()))}
        )

    def with_root(self, root: str | Path | None) -> Prompt:
        return self.model_copy(
            update={"template_root": str(root) if root is not None else None}
        )


def build_prompt(data: dict[str, Any], source: str) -> Prompt:
    try:
        return Prompt(**data)
    except PromptParseError:
        raise
    except Exception as e:
        raise PromptParseError(
            f"Failed to create prompt from {source}: {e}", path=source
        ) from e


__all__ = ["DEFAULT_VERSION", "Prompt", "PromptMetadata", "build_prompt"]
