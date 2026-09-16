from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from promptkit.errors import EvalError
from promptkit.types import Completion

Checker = Callable[["Context", Any], "AssertionResult"]

REGISTRY: dict[str, Checker] = {}


@dataclass(frozen=True, slots=True)
class Context:
    completion: Completion
    duration_seconds: float
    cost: float | None


@dataclass(frozen=True, slots=True)
class AssertionResult:
    kind: str
    passed: bool
    detail: str = ""


def register(name: str) -> Callable[[Checker], Checker]:
    def decorate(fn: Checker) -> Checker:
        REGISTRY[name] = fn

        return fn

    return decorate


def _excerpt(text: str, limit: int = 120) -> str:
    collapsed = " ".join(text.split())

    return collapsed if len(collapsed) <= limit else collapsed[:limit] + "..."


@register("contains")
def _contains(context: Context, expected: Any) -> AssertionResult:
    needles = expected if isinstance(expected, list) else [expected]
    missing = [n for n in needles if str(n) not in context.completion.text]

    return AssertionResult(
        "contains",
        not missing,
        ""
        if not missing
        else f"missing {missing!r} in {_excerpt(context.completion.text)!r}",
    )


@register("not_contains")
def _not_contains(context: Context, expected: Any) -> AssertionResult:
    needles = expected if isinstance(expected, list) else [expected]
    present = [n for n in needles if str(n) in context.completion.text]

    return AssertionResult(
        "not_contains",
        not present,
        "" if not present else f"unexpectedly found {present!r}",
    )


@register("regex")
def _regex(context: Context, pattern: Any) -> AssertionResult:
    try:
        compiled = re.compile(str(pattern), re.MULTILINE)
    except re.error as e:
        raise EvalError(f"invalid regex {pattern!r}: {e}") from e

    matched = compiled.search(context.completion.text) is not None

    return AssertionResult(
        "regex",
        matched,
        ""
        if matched
        else f"{pattern!r} did not match {_excerpt(context.completion.text)!r}",
    )


@register("equals")
def _equals(context: Context, expected: Any) -> AssertionResult:
    actual = context.completion.text.strip()
    passed = actual == str(expected).strip()

    return AssertionResult(
        "equals", passed, "" if passed else f"expected {expected!r}, got {actual!r}"
    )


@register("json_schema")
def _json_schema(context: Context, schema: Any) -> AssertionResult:
    from promptkit.core.jsonschema import compile_json_schema
    from promptkit.core.structured import extract_json

    if not isinstance(schema, dict):
        raise EvalError("json_schema assertion needs a JSON Schema mapping")

    try:
        payload = json.loads(extract_json(context.completion.text))
    except json.JSONDecodeError as e:
        return AssertionResult("json_schema", False, f"output was not JSON: {e}")

    model = compile_json_schema(schema, "EvalOutput")

    try:
        model(**payload)
    except Exception as e:
        return AssertionResult("json_schema", False, str(e).splitlines()[0])

    return AssertionResult("json_schema", True)


@register("is_json")
def _is_json(context: Context, expected: Any) -> AssertionResult:
    from promptkit.core.structured import extract_json

    try:
        json.loads(extract_json(context.completion.text))
    except json.JSONDecodeError as e:
        return AssertionResult("is_json", not expected, f"output was not JSON: {e}")

    return AssertionResult("is_json", bool(expected))


@register("max_latency")
def _max_latency(context: Context, limit: Any) -> AssertionResult:
    passed = context.duration_seconds <= float(limit)

    return AssertionResult(
        "max_latency",
        passed,
        "" if passed else f"took {context.duration_seconds:.2f}s, limit {limit}s",
    )


@register("max_cost")
def _max_cost(context: Context, limit: Any) -> AssertionResult:
    if context.cost is None:
        return AssertionResult("max_cost", True, "cost unknown for this model")

    passed = context.cost <= float(limit)

    return AssertionResult(
        "max_cost",
        passed,
        "" if passed else f"cost ${context.cost:.6f}, limit ${float(limit):.6f}",
    )


@register("max_tokens")
def _max_tokens(context: Context, limit: Any) -> AssertionResult:
    used = context.completion.usage.completion_tokens
    passed = used <= int(limit)

    return AssertionResult(
        "max_tokens", passed, "" if passed else f"used {used} tokens, limit {limit}"
    )


def check(name: str, context: Context, expected: Any) -> AssertionResult:
    checker = REGISTRY.get(name)

    if checker is None:
        known = ", ".join(sorted(REGISTRY))

        raise EvalError(f"unknown assertion '{name}'; available: {known}")

    return checker(context, expected)


def run_assertions(
    assertions: tuple[dict[str, Any], ...], context: Context
) -> list[AssertionResult]:
    results: list[AssertionResult] = []

    for entry in assertions:
        for name, expected in entry.items():
            results.append(check(name, context, expected))

    return results


def names() -> list[str]:
    return sorted(REGISTRY)


__all__ = [
    "REGISTRY",
    "AssertionResult",
    "Context",
    "check",
    "names",
    "register",
    "run_assertions",
]
