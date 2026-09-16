from __future__ import annotations

import importlib
from typing import Any

from promptkit.errors import EngineNotFoundError

DISTRIBUTION = "promptkit-core"


def install_hint(extra: str) -> str:
    return f"pip install '{DISTRIBUTION}[{extra}]'"


def require(module: str, extra: str, engine: str) -> Any:
    try:
        return importlib.import_module(module)
    except ImportError as e:
        raise EngineNotFoundError(engine, install_hint=install_hint(extra)) from e


def is_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


__all__ = ["DISTRIBUTION", "install_hint", "is_available", "require"]
