from __future__ import annotations

import hashlib
import json
from contextlib import suppress
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from promptkit.types import Completion, Message, Usage

SENSITIVE_KEYS = frozenset({"api_key", "key", "authorization", "token", "secret"})


def make_key(
    messages: list[Message],
    model: str,
    options: dict[str, Any] | None = None,
    namespace: str = "",
) -> str:
    payload = {
        "namespace": namespace,
        "model": model,
        "messages": [[m.role, m.content] for m in messages],
        "options": _scrub(options or {}),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _scrub(options: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v
        for k, v in sorted(options.items())
        if k.lower() not in SENSITIVE_KEYS and v is not None
    }


@runtime_checkable
class Cache(Protocol):
    def get(self, key: str) -> Completion | None: ...

    def set(self, key: str, completion: Completion) -> None: ...


class MemoryCache:
    def __init__(self, max_entries: int = 1024) -> None:
        self.max_entries = max_entries
        self._entries: dict[str, Completion] = {}

    def get(self, key: str) -> Completion | None:
        return self._entries.get(key)

    def set(self, key: str, completion: Completion) -> None:
        if len(self._entries) >= self.max_entries:
            self._entries.pop(next(iter(self._entries)), None)

        self._entries[key] = completion

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)


class DiskCache:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def _file(self, key: str) -> Path:
        return self.path / f"{key}.json"

    def get(self, key: str) -> Completion | None:
        file = self._file(key)

        if not file.exists():
            return None

        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        usage = data.get("usage", {})

        return Completion(
            text=data["text"],
            model=data["model"],
            usage=Usage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                estimated=usage.get("estimated", False),
            ),
            finish_reason=data.get("finish_reason"),
        )

    def set(self, key: str, completion: Completion) -> None:
        data = {
            "text": completion.text,
            "model": completion.model,
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "estimated": completion.usage.estimated,
            },
            "finish_reason": completion.finish_reason,
        }

        with suppress(OSError):
            self._file(key).write_text(json.dumps(data), encoding="utf-8")

    def clear(self) -> None:
        for file in self.path.glob("*.json"):
            file.unlink(missing_ok=True)


__all__ = ["Cache", "DiskCache", "MemoryCache", "make_key"]
