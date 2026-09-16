from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator
from yaml.loader import SafeLoader

from promptkit.errors import EvalError

SUITE_SUFFIX = ".evals.yaml"


class EvalCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(...)
    inputs: dict[str, Any] = Field(default_factory=dict)
    assertions: tuple[dict[str, Any], ...] = Field(default=(), alias="assert")
    skip: bool = Field(default=False)

    @field_validator("name", mode="before")
    @classmethod
    def _yaml_scalars_are_names(cls, value: Any) -> Any:
        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(value, int | float):
            return str(value)

        return value


class EvalSuite(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt: str | None = Field(default=None)
    cases: tuple[EvalCase, ...] = Field(default=())

    def __len__(self) -> int:
        return len(self.cases)


def suite_path_for(prompt_path: str | Path) -> Path:
    path = Path(prompt_path)

    return path.with_name(path.stem + SUITE_SUFFIX)


def loads_suite(text: str, source: str = "<string>") -> EvalSuite:
    try:
        data = yaml.load(text, Loader=SafeLoader)
    except yaml.YAMLError as e:
        raise EvalError(f"Failed to parse eval suite {source}: {e}") from e

    if data is None:
        return EvalSuite()

    if isinstance(data, list):
        data = {"cases": data}

    if not isinstance(data, dict):
        raise EvalError(
            f"Eval suite {source} must be a mapping or a list of cases, "
            f"got {type(data).__name__}"
        )

    try:
        return EvalSuite.model_validate(data)
    except Exception as e:
        raise EvalError(f"Invalid eval suite {source}: {e}") from e


def load_suite(path: str | Path) -> EvalSuite:
    file = Path(path)

    if not file.is_file():
        raise EvalError(f"Eval suite not found: {file}")

    return loads_suite(file.read_text(encoding="utf-8"), str(file))


__all__ = [
    "SUITE_SUFFIX",
    "EvalCase",
    "EvalSuite",
    "load_suite",
    "loads_suite",
    "suite_path_for",
]
