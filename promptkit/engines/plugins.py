from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any

from promptkit.engines._sdk import install_hint, is_available
from promptkit.errors import EngineNotFoundError

GROUP = "promptkit.engines"

EXTRA_BY_NAME = {
    "openai": ("openai", "openai"),
    "anthropic": ("anthropic", "anthropic"),
    "ollama": ("ollama", "ollama"),
    "compatible": ("openai", "openai"),
}


@dataclass(frozen=True, slots=True)
class EngineInfo:
    name: str
    target: str
    extra: str | None
    installed: bool

    @property
    def hint(self) -> str | None:
        if self.installed or self.extra is None:
            return None

        return install_hint(self.extra)


def _entries() -> dict[str, Any]:
    return {ep.name: ep for ep in entry_points(group=GROUP)}


def discover() -> dict[str, EngineInfo]:
    found: dict[str, EngineInfo] = {}

    for name, ep in sorted(_entries().items()):
        module, extra = EXTRA_BY_NAME.get(name, (None, None))
        found[name] = EngineInfo(
            name=name,
            target=ep.value,
            extra=extra,
            installed=module is None or is_available(module),
        )

    return found


def names() -> list[str]:
    return sorted(_entries())


def load(name: str) -> type[Any]:
    entry = _entries().get(name)

    if entry is None:
        known = ", ".join(names()) or "none"

        raise EngineNotFoundError(name, install_hint=f"known engines: {known}")

    module, extra = EXTRA_BY_NAME.get(name, (None, None))

    if module is not None and extra is not None and not is_available(module):
        raise EngineNotFoundError(name, install_hint=install_hint(extra))

    loaded: type[Any] = entry.load()

    return loaded


__all__ = ["GROUP", "EngineInfo", "discover", "load", "names"]
