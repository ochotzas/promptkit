from __future__ import annotations

import importlib.util
import re
from functools import lru_cache
from typing import Any

from promptkit.pricing import (
    estimate_cost,
    format_cost,
    list_models,
)

CHARS_PER_TOKEN = 4
FALLBACK_ENCODING = "cl100k_base"
TOKENS_PER_WORD = 1.3
WORD_PATTERN = re.compile(r"\b\w+\b")


def estimate_tokens(text: str) -> int:
    if not text:
        return 0

    char_based = len(text) / CHARS_PER_TOKEN
    word_based = len(WORD_PATTERN.findall(text)) * TOKENS_PER_WORD

    return int(max(char_based, word_based))


def has_exact_counting() -> bool:
    return importlib.util.find_spec("tiktoken") is not None


def _try_load(load: Any) -> Any | None:
    try:
        return load()
    except Exception:
        return None


@lru_cache(maxsize=32)
def _encoding(model: str) -> Any | None:
    import tiktoken

    for load in (
        lambda: tiktoken.encoding_for_model(model),
        lambda: tiktoken.get_encoding(FALLBACK_ENCODING),
    ):
        encoding = _try_load(load)

        if encoding is not None:
            return encoding

    return None


def exact_tokens(text: str, model: str = "gpt-4o-mini") -> int | None:
    if not has_exact_counting():
        return None

    if not text:
        return 0

    encoding = _encoding(model)

    if encoding is None:
        return None

    try:
        return len(encoding.encode(text))
    except Exception:
        return None


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    exact = exact_tokens(text, model)

    return exact if exact is not None else estimate_tokens(text)


def estimate_prompt_cost(prompt_text: str, model: str = "gpt-4o-mini") -> float | None:
    return estimate_cost(estimate_tokens(prompt_text), 0, model)


def list_supported_models() -> list[str]:
    return list_models()


__all__ = [
    "CHARS_PER_TOKEN",
    "count_tokens",
    "estimate_cost",
    "estimate_prompt_cost",
    "estimate_tokens",
    "exact_tokens",
    "format_cost",
    "has_exact_counting",
    "list_supported_models",
]
