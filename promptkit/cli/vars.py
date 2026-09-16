from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from yaml.loader import SafeLoader

from promptkit.core.prompt import Prompt
from promptkit.core.schema import is_optional

TRUTHY = ("true", "yes", "1", "on")
PLACEHOLDERS: dict[str, Any] = {
    "str": "placeholder",
    "int": 42,
    "float": 3.14,
    "bool": True,
    "list": [],
    "dict": {},
}


def parse_pairs(pairs: list[str] | None) -> dict[str, str]:
    parsed: dict[str, str] = {}

    for pair in pairs or []:
        if "=" not in pair:
            raise typer.BadParameter(
                f"--set expects key=value, got {pair!r}", param_hint="--set"
            )

        key, _, raw = pair.partition("=")
        parsed[key.strip()] = raw

    return parsed


def coerce_to(raw: str, type_str: str | None) -> Any:
    if type_str is None:
        return coerce(raw)

    base = type_str.replace(" | None", "").strip()

    if base == "str":
        return raw

    if base == "bool":
        return raw.strip().lower() in TRUTHY

    if base in ("int", "float"):
        convert = int if base == "int" else float

        try:
            return convert(raw.strip())
        except ValueError as e:
            raise typer.BadParameter(
                f"{raw!r} is not a valid {base}", param_hint="--set"
            ) from e

    if base in ("list", "dict"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise typer.BadParameter(
                f"{raw!r} is not valid JSON for a {base}", param_hint="--set"
            ) from e

    return coerce(raw)


def declared_type(prompt: Prompt, field: str) -> str | None:
    from promptkit.core.jsonschema import looks_like_json_schema

    if looks_like_json_schema(prompt.input_schema):
        properties = prompt.input_schema.get("properties") or {}
        entry = properties.get(field)

        if not isinstance(entry, dict):
            return None

        mapping = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }

        return mapping.get(str(entry.get("type")))

    declared = prompt.input_schema.get(field)

    return str(declared) if declared is not None else None


def coerce(raw: str) -> Any:
    text = raw.strip()

    if text.startswith(("{", "[")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return raw

    lowered = text.lower()

    if lowered in TRUTHY:
        return True

    if lowered in ("false", "no", "0", "off"):
        return False

    if lowered == "null":
        return None

    for convert in (int, float):
        try:
            return convert(text)
        except ValueError:
            continue

    return raw


def parse_json(text: str | None, option: str) -> dict[str, Any]:
    if not text:
        return {}

    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"invalid JSON: {e}", param_hint=option) from e

    if not isinstance(loaded, dict):
        raise typer.BadParameter("must be a JSON object", param_hint=option)

    return loaded


def load_file(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}

    if not path.is_file():
        raise typer.BadParameter(f"file not found: {path}", param_hint="--vars-file")

    text = path.read_text(encoding="utf-8")

    try:
        loaded = (
            json.loads(text)
            if path.suffix == ".json"
            else yaml.load(text, Loader=SafeLoader)
        )
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise typer.BadParameter(
            f"could not parse {path}: {e}", param_hint="--vars-file"
        ) from e

    if not isinstance(loaded, dict):
        raise typer.BadParameter(
            f"{path} must contain a mapping", param_hint="--vars-file"
        )

    return loaded


def placeholder_for(type_str: str) -> Any:
    base = type_str.replace(" | None", "").strip()

    return PLACEHOLDERS.get(base, f"placeholder_{base}")


def fill_missing(
    prompt: Prompt,
    values: dict[str, Any],
    console: Console,
    interactive: bool = False,
) -> dict[str, Any]:
    missing = [f for f in prompt.get_required_inputs() if f not in values]

    if not missing:
        return values

    filled = dict(values)

    if not interactive:
        for field in missing:
            filled[field] = placeholder_for(str(prompt.input_schema.get(field, "str")))

        return filled

    console.print(f"[yellow]Missing required inputs: {', '.join(missing)}[/yellow]")

    for field in missing:
        type_str = str(prompt.input_schema.get(field, "str"))
        entered = typer.prompt(f"Enter value for '{field}' ({type_str})")
        filled[field] = coerce_to(entered, type_str)

    return filled


def collect(
    prompt: Prompt,
    console: Console,
    set_pairs: list[str] | None = None,
    vars_json: str | None = None,
    vars_file: Path | None = None,
    interactive: bool = False,
    fill: bool = True,
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    values.update(load_file(vars_file))
    values.update(parse_json(vars_json, "--vars"))
    for field, raw in parse_pairs(set_pairs).items():
        values[field] = coerce_to(raw, declared_type(prompt, field))

    if not fill:
        return values

    return fill_missing(prompt, values, console, interactive)


def describe_inputs(prompt: Prompt) -> list[tuple[str, str, bool]]:
    rows = []

    for field in prompt.get_required_inputs():
        rows.append((field, str(prompt.input_schema.get(field, "str")), True))

    for field in prompt.get_optional_inputs():
        type_str = str(prompt.input_schema.get(field, "str"))
        rows.append((field, type_str.replace(" | None", ""), False))

    return rows


__all__ = [
    "coerce",
    "coerce_to",
    "collect",
    "declared_type",
    "describe_inputs",
    "fill_missing",
    "is_optional",
    "parse_json",
    "parse_pairs",
    "placeholder_for",
]
