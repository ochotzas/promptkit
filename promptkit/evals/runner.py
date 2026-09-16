from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from promptkit.core.prompt import Prompt
from promptkit.engines.base import BaseEngine
from promptkit.errors import EvalError, PromptKitError
from promptkit.evals.assertions import AssertionResult, Context, run_assertions
from promptkit.evals.case import EvalCase, EvalSuite, load_suite, suite_path_for
from promptkit.types import Message

DEFAULT_CONCURRENCY = 4
JUDGE_TEMPLATE = (
    "You are grading a model response against a requirement.\n\n"
    "Requirement: {requirement}\n\n"
    "Response:\n{response}\n\n"
    "Answer with exactly one word: PASS or FAIL."
)


@dataclass(slots=True)
class CaseResult:
    case: str
    passed: bool
    assertions: list[AssertionResult] = field(default_factory=list)
    duration_seconds: float = 0.0
    cost: float | None = None
    error: str | None = None
    skipped: bool = False
    output: str = ""

    @property
    def failures(self) -> list[AssertionResult]:
        return [a for a in self.assertions if not a.passed]


@dataclass(slots=True)
class SuiteResult:
    prompt: str
    results: list[CaseResult] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed and not r.skipped)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed and not r.skipped)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.skipped)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def ok(self) -> bool:
        return self.failed == 0

    @property
    def cost(self) -> float:
        return sum(r.cost or 0.0 for r in self.results)


async def _judge(
    engine: BaseEngine, requirement: str, response: str
) -> AssertionResult:
    question = JUDGE_TEMPLATE.format(requirement=requirement, response=response)
    verdict = await engine.acomplete([Message(role="user", content=question)])
    answer = verdict.text.strip().upper()
    passed = answer.startswith("PASS")

    return AssertionResult(
        "judge", passed, "" if passed else f"judge said: {verdict.text.strip()[:120]}"
    )


def _split_judges(
    assertions: tuple[dict[str, Any], ...],
) -> tuple[tuple[dict[str, Any], ...], list[str]]:
    plain: list[dict[str, Any]] = []
    judges: list[str] = []

    for entry in assertions:
        for name, value in entry.items():
            if name == "judge":
                judges.append(str(value))
            else:
                plain.append({name: value})

    return tuple(plain), judges


async def run_case(
    prompt: Prompt,
    case: EvalCase,
    engine: BaseEngine,
    judge_engine: BaseEngine | None = None,
    **options: Any,
) -> CaseResult:
    if case.skip:
        return CaseResult(case=case.name, passed=True, skipped=True)

    started = time.monotonic()

    try:
        messages = prompt.render_messages(case.inputs)
        completion = await engine.acomplete(messages, **options)
    except PromptKitError as e:
        return CaseResult(
            case=case.name,
            passed=False,
            duration_seconds=time.monotonic() - started,
            error=f"{type(e).__name__}: {e}",
        )

    duration = time.monotonic() - started
    cost = engine.cost_of(completion)
    context = Context(completion=completion, duration_seconds=duration, cost=cost)
    plain, judges = _split_judges(case.assertions)

    try:
        results = run_assertions(plain, context)

        for requirement in judges:
            results.append(
                await _judge(judge_engine or engine, requirement, completion.text)
            )
    except EvalError as e:
        return CaseResult(
            case=case.name,
            passed=False,
            duration_seconds=duration,
            cost=cost,
            error=str(e),
            output=completion.text,
        )

    return CaseResult(
        case=case.name,
        passed=all(r.passed for r in results),
        assertions=results,
        duration_seconds=duration,
        cost=cost,
        output=completion.text,
    )


async def run_suite_async(
    prompt: Prompt,
    suite: EvalSuite,
    engine: BaseEngine,
    judge_engine: BaseEngine | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
    **options: Any,
) -> SuiteResult:
    started = time.monotonic()
    limiter = asyncio.Semaphore(max(1, concurrency))

    async def guarded(case: EvalCase) -> CaseResult:
        async with limiter:
            return await run_case(prompt, case, engine, judge_engine, **options)

    results = await asyncio.gather(*(guarded(case) for case in suite.cases))

    return SuiteResult(
        prompt=prompt.name,
        results=list(results),
        duration_seconds=time.monotonic() - started,
    )


def run_suite(
    prompt: Prompt,
    suite: EvalSuite,
    engine: BaseEngine,
    judge_engine: BaseEngine | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
    **options: Any,
) -> SuiteResult:
    return asyncio.run(
        run_suite_async(prompt, suite, engine, judge_engine, concurrency, **options)
    )


def suite_for(prompt_path: str | Path) -> EvalSuite | None:
    path = suite_path_for(prompt_path)

    return load_suite(path) if path.is_file() else None


__all__ = [
    "DEFAULT_CONCURRENCY",
    "CaseResult",
    "SuiteResult",
    "run_case",
    "run_suite",
    "run_suite_async",
    "suite_for",
]
