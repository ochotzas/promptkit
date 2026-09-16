from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from yaml.loader import SafeLoader

from promptkit.core.compiler import PromptCompiler
from promptkit.core.prompt import Prompt, build_prompt
from promptkit.core.template import ConfinedLoader, resolve_dependencies
from promptkit.errors import PromptNotFoundError, PromptParseError

YAML_SUFFIXES = {".yaml", ".yml"}
REQUIRED_FIELDS = ("name", "description")
CONTENT_FIELDS = ("template", "messages")
KNOWN_FIELDS = frozenset(
    {
        "name",
        "description",
        "version",
        "template",
        "messages",
        "input_schema",
        "output_schema",
        "metadata",
    }
)


def resolve_path(file_path: str | Path) -> Path:
    path = Path(file_path)

    if path.suffix in YAML_SUFFIXES:
        return path

    return path.with_suffix(path.suffix + ".yaml")


def load_prompt(file_path: str | Path, root: str | Path | None = None) -> Prompt:
    path = resolve_path(file_path)

    if not path.exists():
        raise PromptNotFoundError(str(path))

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=SafeLoader)
    except yaml.YAMLError as e:
        raise PromptParseError(
            f"Failed to parse YAML file {path}: {e}", path=str(path)
        ) from e

    if not isinstance(data, dict):
        raise PromptParseError(
            f"Prompt file {path} must contain a mapping, got {type(data).__name__}",
            path=str(path),
        )

    prompt = _from_mapping(data, path)
    template_root = Path(root) if root is not None else path.parent

    return attach_dependencies(prompt, template_root)


def loads_prompt(text: str, source: str = "<string>") -> Prompt:
    try:
        data = yaml.load(text, Loader=SafeLoader)
    except yaml.YAMLError as e:
        raise PromptParseError(f"Failed to parse YAML: {e}", path=source) from e

    if not isinstance(data, dict):
        raise PromptParseError(
            f"Prompt must be a mapping, got {type(data).__name__}", path=source
        )

    return _from_mapping(data, Path(source))


def _from_mapping(data: dict[str, Any], path: Path) -> Prompt:
    missing = [field for field in REQUIRED_FIELDS if field not in data]

    if not any(field in data for field in CONTENT_FIELDS):
        missing.append("template")

    if missing:
        raise PromptParseError(
            f"Missing required fields in {path}: {', '.join(missing)}",
            path=str(path),
            missing_fields=missing,
        )

    schema = data.get("input_schema")

    if schema is not None and not isinstance(schema, dict):
        raise PromptParseError(
            f"input_schema must be a mapping in {path}, got {type(schema).__name__}",
            path=str(path),
        )

    payload = {k: v for k, v in data.items() if k in KNOWN_FIELDS}

    if payload.get("input_schema") is None:
        payload["input_schema"] = {}

    return build_prompt(payload, str(path))


def attach_dependencies(prompt: Prompt, root: Path) -> Prompt:
    if not root.is_dir():
        return prompt

    loader = ConfinedLoader(root)
    compiler = PromptCompiler(loader=loader)
    sources = [m.template for m in prompt.messages]
    dependencies = resolve_dependencies(compiler.env, sources, loader)

    if not dependencies:
        return prompt

    return prompt.with_dependencies(dependencies).with_root(root)


def save_prompt(prompt: Prompt, file_path: str | Path) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {
        "name": prompt.name,
        "description": prompt.description,
        "version": prompt.version,
    }

    if len(prompt.messages) == 1 and prompt.messages[0].role == "user":
        data["template"] = prompt.messages[0].template
    else:
        data["messages"] = [
            {"role": m.role, "template": m.template} for m in prompt.messages
        ]

    data["input_schema"] = prompt.input_schema

    if prompt.output_schema is not None:
        data["output_schema"] = prompt.output_schema

    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)


__all__ = [
    "attach_dependencies",
    "load_prompt",
    "loads_prompt",
    "resolve_path",
    "save_prompt",
]
