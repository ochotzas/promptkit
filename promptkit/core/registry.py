from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from promptkit.core.loader import YAML_SUFFIXES, load_prompt
from promptkit.core.prompt import Prompt
from promptkit.core.template import PARTIAL_PREFIX, is_partial
from promptkit.errors import PromptKitError, PromptNotFoundError

EVAL_SUFFIX = ".evals"
VERSION_SEPARATOR = "@"
LATEST = "latest"


@dataclass(slots=True)
class CacheEntry:
    prompt: Prompt
    mtime: float
    path: Path


def _version_key(version: str) -> tuple[int, ...]:
    parts: list[int] = []

    for chunk in version.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)

    return tuple(parts)


def is_eval_suite(path: Path) -> bool:
    return path.stem.endswith(EVAL_SUFFIX)


def to_identifier(root: Path, path: Path) -> str:
    relative = path.relative_to(root).with_suffix("")

    return ".".join(relative.parts)


def to_relative_path(identifier: str) -> Path:
    return Path(*identifier.split("."))


class PromptRegistry:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._cache: dict[str, CacheEntry] = {}
        self._paths: dict[str, Path] | None = None

    def paths(self, refresh: bool = False) -> dict[str, Path]:
        if self._paths is not None and not refresh:
            return self._paths

        found = self._scan()
        self._paths = found

        return found

    def _scan(self) -> dict[str, Path]:
        found: dict[str, Path] = {}

        if not self.root.is_dir():
            return found

        for suffix in sorted(YAML_SUFFIXES):
            for path in sorted(self.root.rglob(f"*{suffix}")):
                relative = path.relative_to(self.root)

                if is_partial(relative) or is_eval_suite(path):
                    continue

                found.setdefault(to_identifier(self.root, path), path)

        return found

    def names(self) -> list[str]:
        return sorted(self.paths())

    def split_version(self, identifier: str) -> tuple[str, str | None]:
        name, separator, version = identifier.partition(VERSION_SEPARATOR)

        return (name, version or None) if separator else (identifier, None)

    def versions(self, identifier: str) -> dict[str, Path]:
        name, _ = self.split_version(identifier)
        wanted = {name, name.rsplit(".", 1)[-1]}
        found: dict[str, Path] = {}

        for candidate, path in self.paths().items():
            try:
                prompt = load_prompt(path, root=self.root)
            except PromptKitError:
                continue

            if prompt.name not in wanted and candidate not in wanted:
                continue

            found[prompt.version] = path

        return found

    def resolve_version(self, identifier: str) -> Path:
        name, version = self.split_version(identifier)
        available = self.versions(name)

        if not available:
            raise PromptNotFoundError(
                str(self.root / to_relative_path(name)),
                f"No prompt named '{name}' under {self.root}",
            )

        if version is None or version == LATEST:
            return available[max(available, key=_version_key)]

        if version in available:
            return available[version]

        raise PromptNotFoundError(
            str(self.root / to_relative_path(name)),
            f"No version '{version}' of '{name}'; available: "
            f"{', '.join(sorted(available, key=_version_key))}",
        )

    def resolve(self, identifier: str) -> Path:
        if VERSION_SEPARATOR in identifier:
            return self.resolve_version(identifier)

        known = self.paths()

        if identifier in known:
            return known[identifier]

        known = self.paths(refresh=True)

        if identifier in known:
            return known[identifier]

        candidate = self.root / to_relative_path(identifier)

        for suffix in sorted(YAML_SUFFIXES):
            with_suffix = candidate.with_suffix(suffix)

            if with_suffix.is_file():
                return with_suffix

        raise PromptNotFoundError(
            str(candidate),
            f"No prompt named '{identifier}' under {self.root}",
        )

    def get(self, identifier: str) -> Prompt:
        path = self.resolve(identifier)
        mtime = path.stat().st_mtime
        cached = self._cache.get(identifier)

        if cached is not None and cached.mtime == mtime and cached.path == path:
            return cached.prompt

        prompt = load_prompt(path, root=self.root)
        self._cache[identifier] = CacheEntry(prompt=prompt, mtime=mtime, path=path)

        return prompt

    def all(self) -> dict[str, Prompt]:
        return {name: self.get(name) for name in self.names()}

    def partials(self) -> list[str]:
        if not self.root.is_dir():
            return []

        return sorted(
            str(p.relative_to(self.root))
            for p in self.root.rglob("*")
            if p.is_file() and is_partial(p.relative_to(self.root))
        )

    def clear_cache(self) -> None:
        self._cache.clear()
        self._paths = None

    def __getitem__(self, identifier: str) -> Prompt:
        return self.get(identifier)

    def __contains__(self, identifier: str) -> bool:
        return identifier in self.paths()

    def __iter__(self) -> Iterator[str]:
        return iter(self.names())

    def __len__(self) -> int:
        return len(self.paths())

    def __repr__(self) -> str:
        return f"PromptRegistry(root={str(self.root)!r}, prompts={len(self)})"


__all__ = [
    "EVAL_SUFFIX",
    "LATEST",
    "PARTIAL_PREFIX",
    "VERSION_SEPARATOR",
    "CacheEntry",
    "PromptRegistry",
    "is_eval_suite",
    "to_identifier",
]
