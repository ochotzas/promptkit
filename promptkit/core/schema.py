from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, create_model
from pydantic import ValidationError as PydanticValidationError

from promptkit.core.jsonschema import compile_json_schema, looks_like_json_schema
from promptkit.errors import InputValidationError, SchemaError

TYPE_MAPPING: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
}

OPTIONAL_SUFFIX = " | None"


def create_schema_model(schema_dict: dict[str, str]) -> type[BaseModel]:
    field_definitions: dict[str, Any] = {}

    for field_name, type_str in schema_dict.items():
        python_type = parse_type_string(str(type_str), field=field_name)
        default = None if is_optional(str(type_str)) else ...
        field_definitions[field_name] = (python_type, default)

    return create_model("DynamicSchema", **field_definitions)


_model_cache: dict[str, type[BaseModel]] = {}
MAX_MODEL_CACHE = 512


def schema_key(schema: dict[str, Any]) -> str:
    return json.dumps(schema, sort_keys=True, separators=(",", ":"), default=str)


def compile_input_schema(schema: dict[str, Any]) -> type[BaseModel] | None:
    if not schema:
        return None

    key = schema_key(schema)
    cached = _model_cache.get(key)

    if cached is not None:
        return cached

    if looks_like_json_schema(schema):
        model = compile_json_schema(schema, "InputSchema")
    else:
        model = create_schema_model({k: str(v) for k, v in schema.items()})

    if len(_model_cache) >= MAX_MODEL_CACHE:
        _model_cache.pop(next(iter(_model_cache)), None)

    _model_cache[key] = model

    return model


def clear_model_cache() -> None:
    _model_cache.clear()


def is_optional(type_str: str) -> bool:
    return OPTIONAL_SUFFIX in type_str


def parse_type_string(type_str: str, field: str | None = None) -> Any:
    type_str = type_str.strip()

    if is_optional(type_str):
        base = parse_basic_type(type_str.replace(OPTIONAL_SUFFIX, "").strip(), field)

        return base | None

    return parse_basic_type(type_str, field)


def parse_basic_type(type_str: str, field: str | None = None) -> type:
    try:
        return TYPE_MAPPING[type_str]
    except KeyError:
        supported = ", ".join(sorted(TYPE_MAPPING))
        location = f" for field '{field}'" if field else ""

        raise SchemaError(
            f"Unsupported type '{type_str}'{location}. The type-string language is"
            f" frozen at: {supported} (append '{OPTIONAL_SUFFIX}' for optional)."
            " For anything richer, use a JSON Schema object instead.",
            field=field,
        ) from None


def validate_inputs(
    inputs: dict[str, Any], schema_dict: dict[str, Any]
) -> dict[str, Any]:
    model = compile_input_schema(schema_dict)

    if model is None:
        return inputs

    try:
        validated = model(**inputs)
    except PydanticValidationError as e:
        raise InputValidationError(f"Input validation failed: {e}", cause=e) from e

    return validated.model_dump()


__all__ = [
    "MAX_MODEL_CACHE",
    "OPTIONAL_SUFFIX",
    "TYPE_MAPPING",
    "clear_model_cache",
    "compile_input_schema",
    "create_schema_model",
    "is_optional",
    "parse_basic_type",
    "parse_type_string",
    "validate_inputs",
]
