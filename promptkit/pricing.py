from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Literal, NamedTuple

DATA_FILE = Path(__file__).parent / "data" / "pricing.json"
TOKENS_PER_UNIT = 1_000_000

SNAPSHOT_SUFFIX = re.compile(r"-(?:\d{8}|\d{4}-\d{2}-\d{2}|latest|v\d+)$")

MatchKind = Literal["exact", "snapshot", "override"]


class ModelPricing(NamedTuple):
    input_per_million: float
    output_per_million: float


class PriceLookup(NamedTuple):
    requested: str
    matched: str
    pricing: ModelPricing
    kind: MatchKind

    @property
    def exact(self) -> bool:
        return self.kind != "snapshot"

    def describe(self) -> str:
        if self.kind == "override":
            return f"{self.matched} (registered override)"

        if self.kind == "snapshot":
            return f"{self.matched} (dated snapshot of {self.requested})"

        return self.matched


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, ModelPricing], str]:
    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, "unknown"

    models = {
        name: ModelPricing(float(entry["input"]), float(entry["output"]))
        for name, entry in payload.get("models", {}).items()
        if "input" in entry and "output" in entry
    }

    return models, str(payload.get("_meta", {}).get("updated", "unknown"))


def _table() -> dict[str, ModelPricing]:
    return _load()[0]


PRICING_UPDATED = _load()[1]
PRICING: Mapping[str, ModelPricing] = MappingProxyType(_table())

_overrides: dict[str, ModelPricing] = {}


def register_pricing(
    model: str, input_per_million: float, output_per_million: float
) -> None:
    _overrides[model] = ModelPricing(input_per_million, output_per_million)


def clear_overrides() -> None:
    _overrides.clear()


def base_name(model: str) -> str | None:
    stripped = SNAPSHOT_SUFFIX.sub("", model)

    return stripped if stripped != model else None


def lookup(model: str) -> PriceLookup | None:
    if model in _overrides:
        return PriceLookup(model, model, _overrides[model], "override")

    table = _table()

    if model in table:
        return PriceLookup(model, model, table[model], "exact")

    base = base_name(model)

    if base is None:
        return None

    if base in _overrides:
        return PriceLookup(model, base, _overrides[base], "snapshot")

    if base in table:
        return PriceLookup(model, base, table[base], "snapshot")

    return None


def get_pricing(model: str) -> ModelPricing | None:
    found = lookup(model)

    return found.pricing if found is not None else None


def list_models() -> list[str]:
    return sorted({**_table(), **_overrides})


def estimate_cost(
    input_tokens: int, output_tokens: int = 0, model: str = "gpt-4o-mini"
) -> float | None:
    pricing = get_pricing(model)

    if pricing is None:
        return None

    return (
        input_tokens * pricing.input_per_million
        + output_tokens * pricing.output_per_million
    ) / TOKENS_PER_UNIT


def format_cost(cost: float) -> str:
    if cost >= 0.01:
        return f"${cost:.4f}"

    return f"${cost:.6f}"


__all__ = [
    "PRICING",
    "PRICING_UPDATED",
    "TOKENS_PER_UNIT",
    "MatchKind",
    "ModelPricing",
    "PriceLookup",
    "base_name",
    "clear_overrides",
    "estimate_cost",
    "format_cost",
    "get_pricing",
    "list_models",
    "lookup",
    "register_pricing",
]
