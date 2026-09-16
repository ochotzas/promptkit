from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from promptkit.errors import OutputValidationError
from promptkit.types import Completion, Message

T = TypeVar("T", bound=BaseModel)

DEFAULT_PARSE_RETRIES = 2
FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


@dataclass(frozen=True, slots=True)
class ParsedCompletion(Generic[T]):
    value: T
    completion: Completion

    @property
    def text(self) -> str:
        return self.completion.text

    def __str__(self) -> str:
        return self.completion.text


def extract_json(text: str) -> str:
    stripped = text.strip()
    fenced = FENCE.search(stripped)

    if fenced:
        return fenced.group(1).strip()

    for opener, closer in (("{", "}"), ("[", "]")):
        start = stripped.find(opener)
        end = stripped.rfind(closer)

        if start != -1 and end > start:
            return stripped[start : end + 1]

    return stripped


def parse_output(text: str, model: type[T]) -> T:
    payload = extract_json(text)

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise OutputValidationError(f"Model output was not valid JSON: {e}") from e

    if not isinstance(data, dict):
        raise OutputValidationError(
            f"Model output must be a JSON object, got {type(data).__name__}"
        )

    try:
        return model(**data)
    except PydanticValidationError as e:
        raise OutputValidationError(
            f"Model output did not match the expected schema: {e}", cause=e
        ) from e


def schema_instruction(model: type[BaseModel]) -> str:
    schema = json.dumps(model.model_json_schema(), indent=2, sort_keys=True)

    return (
        "Respond with a single JSON object that validates against this JSON Schema. "
        "Return only the JSON, with no prose and no code fence.\n\n"
        f"{schema}"
    )


def repair_message(error: Exception, previous: str) -> list[Message]:
    return [
        Message(role="assistant", content=previous),
        Message(
            role="user",
            content=(
                "That response could not be parsed. "
                f"The error was:\n\n{error}\n\n"
                "Return corrected JSON only, with no prose and no code fence."
            ),
        ),
    ]


def prepare(
    messages: list[Message], model: type[BaseModel], json_mode: bool
) -> tuple[list[Message], dict[str, Any]]:
    if json_mode:
        return messages, {"json_schema": model.model_json_schema()}

    instruction = Message(role="system", content=schema_instruction(model))

    return [*messages, instruction], {}


__all__ = [
    "DEFAULT_PARSE_RETRIES",
    "ParsedCompletion",
    "extract_json",
    "parse_output",
    "prepare",
    "repair_message",
    "schema_instruction",
]
