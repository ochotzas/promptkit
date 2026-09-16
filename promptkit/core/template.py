from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from pathlib import Path

from jinja2 import BaseLoader, Environment, TemplateNotFound, meta

from promptkit.errors import TemplateError

MAX_INCLUDE_DEPTH = 10
PARTIAL_PREFIX = "_"
TEMPLATE_SUFFIXES = (".j2", ".jinja", ".jinja2", ".txt", ".md")


def is_partial(relative: str | Path) -> bool:
    return any(part.startswith(PARTIAL_PREFIX) for part in Path(relative).parts)


def _reject(name: str, reason: str) -> TemplateError:
    return TemplateError(
        f"refusing to load template '{name}': {reason}", template_name=name
    )


def safe_join(root: Path, name: str) -> Path:
    if not name:
        raise _reject(name, "empty template name")

    if "\x00" in name:
        raise _reject(name, "null byte in template name")

    candidate = PurePosixLike(name)

    if candidate.is_absolute:
        raise _reject(name, "absolute paths are not allowed")

    if candidate.has_drive:
        raise _reject(name, "drive-qualified paths are not allowed")

    normalized = os.path.normpath(candidate.as_posix)

    if normalized.startswith("..") or normalized == ".":
        raise _reject(name, "path escapes the template root")

    target = root / normalized

    try:
        resolved = target.resolve(strict=False)
    except OSError as e:
        raise _reject(name, f"path could not be resolved: {e}") from e

    if not _is_within(resolved, root.resolve(strict=False)):
        raise _reject(name, "resolved path escapes the template root")

    return resolved


class PurePosixLike:
    def __init__(self, name: str) -> None:
        self.raw = name.replace("\\", "/")

    @property
    def is_absolute(self) -> bool:
        return self.raw.startswith("/")

    @property
    def has_drive(self) -> bool:
        return len(self.raw) > 1 and self.raw[1] == ":"

    @property
    def as_posix(self) -> str:
        return self.raw


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False

    return True


class ConfinedLoader(BaseLoader):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve(strict=False)

    def get_source(
        self, environment: Environment, template: str
    ) -> tuple[str, str, Callable[[], bool]]:
        path = safe_join(self.root, template)

        if not path.is_file():
            raise TemplateNotFound(template)

        try:
            source = path.read_text(encoding="utf-8")
            mtime = path.stat().st_mtime
        except OSError as e:
            raise _reject(template, f"unreadable: {e}") from e

        def uptodate() -> bool:
            try:
                return path.stat().st_mtime == mtime
            except OSError:
                return False

        return source, str(path), uptodate

    def read(self, template: str) -> str:
        path = safe_join(self.root, template)

        if not path.is_file():
            raise TemplateError(
                f"template '{template}' not found under {self.root}",
                template_name=template,
            )

        return path.read_text(encoding="utf-8")

    def list_templates(self) -> list[str]:
        found = [
            str(p.relative_to(self.root))
            for p in sorted(self.root.rglob("*"))
            if p.is_file() and p.suffix in TEMPLATE_SUFFIXES
        ]

        return found


def referenced_templates(environment: Environment, source: str) -> list[str]:
    try:
        parsed = environment.parse(source)
    except Exception as e:
        raise TemplateError(f"Template compilation failed: {e}") from e

    return sorted(name for name in meta.find_referenced_templates(parsed) if name)


def resolve_dependencies(
    environment: Environment,
    sources: list[str],
    loader: ConfinedLoader | None,
    max_depth: int = MAX_INCLUDE_DEPTH,
) -> dict[str, str]:
    if loader is None:
        return {}

    resolved: dict[str, str] = {}
    frontier = [(source, 0) for source in sources]

    while frontier:
        source, depth = frontier.pop()

        if depth > max_depth:
            raise TemplateError(
                f"include depth exceeded {max_depth}; check for a cycle in partials"
            )

        for name in referenced_templates(environment, source):
            if name in resolved:
                continue

            child = loader.read(name)
            resolved[name] = hashlib.sha256(child.encode("utf-8")).hexdigest()
            frontier.append((child, depth + 1))

    return resolved


__all__ = [
    "MAX_INCLUDE_DEPTH",
    "PARTIAL_PREFIX",
    "ConfinedLoader",
    "is_partial",
    "referenced_templates",
    "resolve_dependencies",
    "safe_join",
]
