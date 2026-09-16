from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

SUITE_SUFFIX = ".evals.yaml"
ENGINE_KEY: pytest.StashKey[Any] = pytest.StashKey()


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("promptkit")
    group.addoption(
        "--promptkit-record",
        action="store_true",
        default=False,
        help="Call the provider and record responses into the cassette",
    )
    parser.addini(
        "promptkit_evals",
        "Collect PromptKit eval suites (*.evals.yaml) as tests",
        type="bool",
        default=True,
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "promptkit: a PromptKit eval case")
    config.stash.setdefault(ENGINE_KEY, None)


def pytest_collect_file(parent: Any, file_path: Path) -> Any:
    if not file_path.name.endswith(SUITE_SUFFIX):
        return None

    if not parent.config.getini("promptkit_evals"):
        return None

    return EvalFile.from_parent(parent, path=file_path)


def prompt_for(suite_path: Path) -> Any:
    from promptkit.core.loader import load_prompt
    from promptkit.errors import EvalError

    stem = suite_path.name.removesuffix(SUITE_SUFFIX)

    for suffix in (".yaml", ".yml"):
        candidate = suite_path.with_name(stem + suffix)

        if candidate.is_file():
            return load_prompt(candidate, root=suite_path.parent)

    raise EvalError(f"No prompt file found next to {suite_path.name}")


class EvalFile(pytest.File):
    def collect(self) -> Any:
        from promptkit.errors import PromptKitError
        from promptkit.evals.case import load_suite

        try:
            suite = load_suite(self.path)
            prompt = prompt_for(self.path)
        except PromptKitError as e:
            raise pytest.UsageError(f"{self.path}: {e}") from e

        for case in suite.cases:
            yield EvalItem.from_parent(self, name=case.name, case=case, prompt=prompt)


class EvalItem(pytest.Item):
    def __init__(self, *, case: Any, prompt: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.case = case
        self.prompt = prompt
        self.add_marker(pytest.mark.promptkit)

    def runtest(self) -> None:
        import asyncio

        from promptkit.evals.cassette import (
            Cassette,
            CassetteEngine,
            Mode,
            cassette_path_for,
        )
        from promptkit.evals.runner import run_case

        if self.case.skip:
            pytest.skip("marked skip in the eval suite")

        record = bool(self.config.getoption("--promptkit-record"))
        cassette = Cassette.load(cassette_path_for(self.path))
        engine = self.config.stash.get(ENGINE_KEY, None)
        offline = engine is None

        if offline and not len(cassette) and not record:
            pytest.skip(
                "no cassette recorded and no engine configured; record one with "
                "'promptkit test <prompt> --record'"
            )

        if offline:
            engine = _ReplayOnly()

        mode: Mode = "record" if record else ("replay" if offline else "auto")
        wrapped = CassetteEngine(cast("Any", engine), cassette, mode)

        try:
            result = asyncio.run(run_case(self.prompt, self.case, wrapped))
        finally:
            cassette.save()

        if result.error is not None or not result.passed:
            raise EvalFailureError(result)

    def repr_failure(self, excinfo: Any, style: Any = None) -> Any:
        if isinstance(excinfo.value, EvalFailureError):
            return excinfo.value.describe()

        return super().repr_failure(excinfo, style)

    def reportinfo(self) -> tuple[Path, int, str]:
        return self.path, 0, f"eval: {self.prompt.name}::{self.case.name}"


class EvalFailureError(Exception):
    def __init__(self, result: Any) -> None:
        self.result = result
        super().__init__(result.error or "assertion failed")

    def describe(self) -> str:
        if self.result.error is not None:
            return f"{self.result.case}: {self.result.error}"

        lines = [f"{self.result.case}: {len(self.result.failures)} assertion(s) failed"]

        for failure in self.result.failures:
            lines.append(f"  {failure.kind}: {failure.detail or 'failed'}")

        if self.result.output:
            excerpt = " ".join(self.result.output.split())[:200]
            lines.append(f"  output: {excerpt}")

        return "\n".join(lines)


class _ReplayOnly:
    model = "cassette"

    def _fail(self) -> Exception:
        from promptkit.errors import EvalError

        return EvalError("no engine configured and no recording for this call")

    def complete(self, messages: Any, **options: Any) -> Any:
        raise self._fail()

    async def acomplete(self, messages: Any, **options: Any) -> Any:
        raise self._fail()

    def cost_of(self, completion: Any) -> float | None:
        return None

    def close(self) -> None:
        return None

    async def aclose(self) -> None:
        return None


__all__ = ["ENGINE_KEY", "EvalFile", "EvalItem", "prompt_for"]
