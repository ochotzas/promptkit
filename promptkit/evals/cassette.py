from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Literal

from promptkit.cache import make_key
from promptkit.engines.base import BaseEngine
from promptkit.errors import EvalError
from promptkit.types import Capabilities, Completion, Message, Usage

CASSETTE_SUFFIX = ".cassette.json"
CASSETTE_SCOPE = "recorded"
Mode = Literal["auto", "record", "replay", "off"]


def cassette_path_for(prompt_path: str | Path) -> Path:
    path = Path(prompt_path)
    stem = path.name.removesuffix(".evals.yaml").removesuffix(path.suffix)

    return path.with_name(stem + CASSETTE_SUFFIX)


@dataclass(slots=True)
class Cassette:
    path: Path
    entries: dict[str, dict[str, Any]] = field(default_factory=dict)
    dirty: bool = False

    @classmethod
    def load(cls, path: str | Path) -> Cassette:
        file = Path(path)

        if not file.is_file():
            return cls(path=file)

        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise EvalError(f"Could not read cassette {file}: {e}") from e

        return cls(path=file, entries=dict(payload.get("entries", {})))

    def get(self, key: str) -> Completion | None:
        entry = self.entries.get(key)

        if entry is None:
            return None

        usage = entry.get("usage", {})

        return Completion(
            text=entry["text"],
            model=entry["model"],
            usage=Usage(
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
                estimated=bool(usage.get("estimated", False)),
            ),
            finish_reason=entry.get("finish_reason"),
        )

    def put(self, key: str, completion: Completion) -> None:
        self.entries[key] = {
            "text": completion.text,
            "model": completion.model,
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "estimated": completion.usage.estimated,
            },
            "finish_reason": completion.finish_reason,
        }
        self.dirty = True

    def save(self) -> None:
        if not self.dirty:
            return

        payload = {
            "version": 1,
            "note": "Recorded by promptkit. Regenerate with promptkit test --record.",
            "entries": dict(sorted(self.entries.items())),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
        )
        self.dirty = False

    def __len__(self) -> int:
        return len(self.entries)

    def __contains__(self, key: str) -> bool:
        return key in self.entries


class CassetteEngine(BaseEngine):
    capabilities: ClassVar[Capabilities] = Capabilities(
        streaming=False, json_mode=False, system_role=True
    )

    def __init__(
        self, engine: BaseEngine, cassette: Cassette, mode: Mode = "auto"
    ) -> None:
        super().__init__(engine.model)
        self.engine = engine
        self.cassette = cassette
        self.mode = mode
        self.hits = 0
        self.misses = 0

    @property
    def capabilities_of_inner(self) -> Capabilities:
        return self.engine.capabilities

    def _key(self, messages: list[Message], options: dict[str, Any]) -> str:
        return make_key(messages, CASSETTE_SCOPE, options, namespace="cassette")

    def _replay(self, key: str) -> Completion | None:
        if self.mode in ("auto", "replay"):
            return self.cassette.get(key)

        return None

    def _missing(self, key: str) -> EvalError:
        if len(self.cassette):
            return EvalError(
                f"{self.cassette.path.name} has {len(self.cassette)} recording(s) "
                "but none for this call. The prompt or the case inputs changed "
                "since it was recorded. Re-record with: "
                "promptkit test <prompt> --record"
            )

        return EvalError(
            f"{self.cassette.path.name} is empty. "
            "Record it with: promptkit test <prompt> --record"
        )

    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        key = self._key(messages, options)
        found = self._replay(key)

        if found is not None:
            self.hits += 1

            return found

        if self.mode == "replay":
            raise self._missing(key)

        self.misses += 1
        completion = self.engine.complete(messages, **options)
        self.cassette.put(key, completion)

        return completion

    async def _acomplete(self, messages: list[Message], **options: Any) -> Completion:
        key = self._key(messages, options)
        found = self._replay(key)

        if found is not None:
            self.hits += 1

            return found

        if self.mode == "replay":
            raise self._missing(key)

        self.misses += 1
        completion = await self.engine.acomplete(messages, **options)
        self.cassette.put(key, completion)

        return completion

    def close(self) -> None:
        self.cassette.save()
        self.engine.close()

    async def aclose(self) -> None:
        self.cassette.save()
        await self.engine.aclose()


class OfflineEngine(BaseEngine):
    capabilities: ClassVar[Capabilities] = Capabilities(
        streaming=False, json_mode=False, system_role=True
    )

    def __init__(self, model: str = "offline") -> None:
        super().__init__(model)

    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        raise EvalError(
            "No engine is configured and the cassette has no recording for this call. "
            "Record one with: promptkit test <prompt> --record --engine openai"
        )


__all__ = [
    "CASSETTE_SCOPE",
    "CASSETTE_SUFFIX",
    "Cassette",
    "CassetteEngine",
    "Mode",
    "OfflineEngine",
    "cassette_path_for",
]
