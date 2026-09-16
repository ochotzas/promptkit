from __future__ import annotations

from enum import Enum
from types import GenericAlias
from typing import Any, Literal

from pydantic import BaseModel, Field, create_model

from promptkit.errors import SchemaError

JSON_SCHEMA_TYPES = frozenset(
    {"object", "array", "string", "integer", "number", "boolean", "null"}
)

SCALARS: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}

DEF_KEYS = ("$defs", "definitions")


def looks_like_json_schema(schema: dict[str, Any]) -> bool:
    if not schema:
        return False

    if "properties" in schema or "$schema" in schema:
        return True

    declared = schema.get("type")

    return isinstance(declared, str) and declared in JSON_SCHEMA_TYPES


def compile_json_schema(
    schema: dict[str, Any], name: str = "GeneratedSchema"
) -> type[BaseModel]:
    if not isinstance(schema, dict):
        raise SchemaError(f"JSON Schema must be a mapping, got {type(schema).__name__}")

    declared = schema.get("type", "object")

    if declared != "object":
        raise SchemaError(f"top-level JSON Schema must be an object, got '{declared}'")

    return _object_model(schema, schema, name)


def _defs(root: dict[str, Any]) -> dict[str, Any]:
    for key in DEF_KEYS:
        found = root.get(key)

        if isinstance(found, dict):
            return found

    return {}


def _deref(schema: dict[str, Any], root: dict[str, Any], field: str) -> dict[str, Any]:
    ref = schema.get("$ref")

    if ref is None:
        return schema

    if not isinstance(ref, str) or not ref.startswith("#/"):
        raise SchemaError(
            f"only local '#/$defs/...' references are supported, got '{ref}'",
            field=field,
        )

    target = ref.rsplit("/", 1)[-1]
    resolved = _defs(root).get(target)

    if not isinstance(resolved, dict):
        raise SchemaError(f"reference '{ref}' could not be resolved", field=field)

    return resolved


def _object_model(
    schema: dict[str, Any], root: dict[str, Any], name: str
) -> type[BaseModel]:
    properties = schema.get("properties")

    if not isinstance(properties, dict):
        raise SchemaError(f"object schema '{name}' has no 'properties' mapping")

    required = set(schema.get("required") or ())
    fields: dict[str, Any] = {}

    for field_name, raw in properties.items():
        if not isinstance(raw, dict):
            raise SchemaError(
                f"property '{field_name}' must be a mapping", field=field_name
            )

        python_type = _type_of(raw, root, field_name)
        description = raw.get("description")

        if field_name in required:
            default: Any = ...
        else:
            default = raw.get("default")
            python_type = python_type | None

        fields[field_name] = (
            python_type,
            Field(default, description=description) if description else default,
        )

    return create_model(name, **fields)


def _type_of(schema: dict[str, Any], root: dict[str, Any], field: str) -> Any:
    schema = _deref(schema, root, field)
    choices = schema.get("enum")

    if choices is not None:
        return _enum_type(choices, field)

    declared = schema.get("type")

    if isinstance(declared, list):
        return _union_of(declared, schema, root, field)

    if declared is None:
        return Any

    return _single_type(str(declared), schema, root, field)


def _single_type(
    declared: str, schema: dict[str, Any], root: dict[str, Any], field: str
) -> Any:
    if declared in SCALARS:
        return SCALARS[declared]

    if declared == "null":
        return type(None)

    if declared == "array":
        items = schema.get("items")

        if not isinstance(items, dict):
            return list[Any]

        return GenericAlias(list, (_type_of(items, root, field),))

    if declared == "object":
        if "properties" in schema:
            return _object_model(schema, root, _model_name(field))

        return dict[str, Any]

    raise SchemaError(
        f"unsupported JSON Schema type '{declared}'"
        f" (supported: {', '.join(sorted(JSON_SCHEMA_TYPES))})",
        field=field,
    )


def _union_of(
    declared: list[Any], schema: dict[str, Any], root: dict[str, Any], field: str
) -> Any:
    members = [_single_type(str(entry), schema, root, field) for entry in declared]

    if not members:
        raise SchemaError("empty type list", field=field)

    combined = members[0]

    for member in members[1:]:
        combined = combined | member

    return combined


def _enum_type(choices: Any, field: str) -> Any:
    if not isinstance(choices, list) or not choices:
        raise SchemaError("'enum' must be a non-empty list", field=field)

    if all(isinstance(c, str) for c in choices):
        return _literal_of(choices)

    return Enum(_model_name(field) + "Enum", {str(c): c for c in choices})


def _literal_of(values: list[Any]) -> Any:
    return Literal.__getitem__(tuple(values))


def _model_name(field: str) -> str:
    return (
        "".join(part.title() for part in field.replace("-", "_").split("_")) or "Nested"
    )


__all__ = [
    "JSON_SCHEMA_TYPES",
    "compile_json_schema",
    "looks_like_json_schema",
]
