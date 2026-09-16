from __future__ import annotations

import json
from typing import Any
from xml.etree.ElementTree import fromstring

import pytest

from promptkit.core.prompt import Prompt
from promptkit.engines.base import BaseEngine
from promptkit.errors import EvalError, ProviderError
from promptkit.evals.assertions import Context, check, names, run_assertions
from promptkit.evals.case import loads_suite, suite_path_for
from promptkit.evals.report import to_dict, to_json, to_junit, to_terminal
from promptkit.evals.runner import SuiteResult, run_suite
from promptkit.types import Completion, Message, Usage


def context(
    text: str = "Hello Alice!", duration: float = 0.1, cost: float | None = 0.001
) -> Context:
    return Context(
        completion=Completion(text=text, model="gpt-4o-mini", usage=Usage(10, 5)),
        duration_seconds=duration,
        cost=cost,
    )


class Echo(BaseEngine):
    def __init__(self, text: str = "Hello Alice!", **kw: Any) -> None:
        super().__init__("gpt-4o-mini", **kw)
        self.text = text

    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        return Completion(text=self.text, model=self.model, usage=Usage(10, 5))


class Broken(BaseEngine):
    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        raise ProviderError("upstream down", model=self.model, status_code=500)


@pytest.fixture
def prompt() -> Prompt:
    return Prompt(
        name="greet", description="d", template="Hi {{ n }}", input_schema={"n": "str"}
    )


class TestAssertions:
    def test_registry_is_populated(self) -> None:
        assert {"contains", "regex", "max_cost", "json_schema"} <= set(names())

    def test_contains_single_and_list(self) -> None:
        assert check("contains", context(), "Alice").passed
        assert check("contains", context(), ["Alice", "Hello"]).passed

    def test_contains_reports_what_is_missing(self) -> None:
        result = check("contains", context(), "Bob")

        assert not result.passed
        assert "Bob" in result.detail

    def test_not_contains(self) -> None:
        assert check("not_contains", context(), "Bob").passed
        assert not check("not_contains", context(), "Alice").passed

    def test_regex(self) -> None:
        assert check("regex", context(), "^Hello").passed
        assert not check("regex", context(), "^Goodbye").passed

    def test_invalid_regex_raises(self) -> None:
        with pytest.raises(EvalError, match="invalid regex"):
            check("regex", context(), "[unclosed")

    def test_equals(self) -> None:
        assert check("equals", context("exact"), "exact").passed
        assert not check("equals", context("exact"), "other").passed

    def test_max_latency(self) -> None:
        assert check("max_latency", context(duration=0.1), 1.0).passed
        assert not check("max_latency", context(duration=2.0), 1.0).passed

    def test_max_cost(self) -> None:
        assert check("max_cost", context(cost=0.001), 0.01).passed
        assert not check("max_cost", context(cost=0.1), 0.01).passed

    def test_max_cost_passes_when_cost_unknown(self) -> None:
        assert check("max_cost", context(cost=None), 0.01).passed

    def test_max_tokens(self) -> None:
        assert check("max_tokens", context(), 10).passed
        assert not check("max_tokens", context(), 1).passed

    def test_is_json(self) -> None:
        assert check("is_json", context('{"a": 1}'), True).passed
        assert check("is_json", context("not json"), False).passed

    def test_json_schema(self) -> None:
        schema = {
            "type": "object",
            "properties": {"a": {"type": "integer"}},
            "required": ["a"],
        }

        assert check("json_schema", context('{"a": 1}'), schema).passed
        assert not check("json_schema", context('{"a": "x"}'), schema).passed

    def test_json_schema_on_non_json(self) -> None:
        schema = {"type": "object", "properties": {}}
        result = check("json_schema", context("nope"), schema)

        assert not result.passed
        assert "not JSON" in result.detail

    def test_unknown_assertion_lists_the_known_ones(self) -> None:
        with pytest.raises(EvalError, match="unknown assertion"):
            check("teleport", context(), True)

    def test_run_assertions_flattens_entries(self) -> None:
        results = run_assertions(
            ({"contains": "Alice"}, {"not_contains": "Bob"}), context()
        )

        assert [r.kind for r in results] == ["contains", "not_contains"]


class TestSuiteParsing:
    def test_cases_with_assert_alias(self) -> None:
        suite = loads_suite(
            "cases:\n  - name: a\n    inputs: {n: x}\n"
            "    assert:\n      - contains: x\n"
        )

        assert suite.cases[0].assertions == ({"contains": "x"},)

    def test_bare_list_of_cases(self) -> None:
        suite = loads_suite("- name: a\n  inputs: {n: x}\n")

        assert len(suite) == 1

    def test_empty_suite(self) -> None:
        assert len(loads_suite("")) == 0

    def test_invalid_yaml_raises(self) -> None:
        with pytest.raises(EvalError, match="Failed to parse"):
            loads_suite("cases: [unclosed")

    def test_scalar_suite_raises(self) -> None:
        with pytest.raises(EvalError, match="must be a mapping"):
            loads_suite("just a string")

    def test_yaml_boolean_case_names_survive(self) -> None:
        suite = loads_suite("cases:\n  - name: no\n  - name: on\n  - name: 2\n")

        assert [c.name for c in suite.cases] == ["false", "true", "2"]

    def test_suite_path_convention(self) -> None:
        assert suite_path_for("prompts/greet.yaml").name == "greet.evals.yaml"


class TestRunner:
    def test_passing_suite(self, prompt: Prompt) -> None:
        suite = loads_suite(
            "cases:\n  - name: ok\n    inputs: {n: Alice}\n"
            "    assert:\n      - contains: Alice\n"
        )
        result = run_suite(prompt, suite, Echo())

        assert result.ok
        assert (result.passed, result.failed, result.skipped) == (1, 0, 0)

    def test_failing_suite(self, prompt: Prompt) -> None:
        suite = loads_suite(
            "cases:\n  - name: wrong_name\n    inputs: {n: Alice}\n"
            "    assert:\n      - contains: Bob\n"
        )
        result = run_suite(prompt, suite, Echo())

        assert not result.ok
        assert result.results[0].failures[0].kind == "contains"

    def test_skipped_case(self, prompt: Prompt) -> None:
        suite = loads_suite(
            "cases:\n  - name: later\n    skip: true\n    inputs: {n: x}\n"
        )
        result = run_suite(prompt, suite, Echo())

        assert result.skipped == 1
        assert result.ok

    def test_engine_error_becomes_a_failed_case(self, prompt: Prompt) -> None:
        from promptkit.retry import NO_RETRY

        suite = loads_suite("cases:\n  - name: a\n    inputs: {n: x}\n")
        result = run_suite(prompt, suite, Broken("m", retry=NO_RETRY))

        assert not result.ok
        assert result.results[0].error is not None
        assert "upstream down" in result.results[0].error

    def test_input_validation_error_is_reported(self, prompt: Prompt) -> None:
        suite = loads_suite("cases:\n  - name: a\n    inputs: {}\n")
        result = run_suite(prompt, suite, Echo())

        assert not result.ok
        assert "InputValidationError" in (result.results[0].error or "")

    def test_bad_assertion_is_reported_per_case(self, prompt: Prompt) -> None:
        suite = loads_suite(
            "cases:\n  - name: a\n    inputs: {n: x}\n"
            "    assert:\n      - teleport: true\n"
        )
        result = run_suite(prompt, suite, Echo())

        assert not result.ok
        assert "unknown assertion" in (result.results[0].error or "")

    def test_many_cases_run_concurrently(self, prompt: Prompt) -> None:
        cases = "".join(
            f"  - name: c{i}\n    inputs: {{n: x}}\n"
            "    assert:\n      - contains: Hello\n"
            for i in range(12)
        )
        result = run_suite(
            prompt, loads_suite(f"cases:\n{cases}"), Echo(), concurrency=4
        )

        assert result.passed == 12

    def test_cost_is_accumulated(self, prompt: Prompt) -> None:
        suite = loads_suite("cases:\n  - name: a\n    inputs: {n: x}\n")

        assert run_suite(prompt, suite, Echo()).cost > 0

    def test_judge_assertion_uses_the_engine(self, prompt: Prompt) -> None:
        suite = loads_suite(
            "cases:\n  - name: a\n    inputs: {n: x}\n"
            "    assert:\n      - judge: Is this polite?\n"
        )
        result = run_suite(prompt, suite, Echo(), judge_engine=Echo("PASS"))

        assert result.ok

    def test_judge_can_fail(self, prompt: Prompt) -> None:
        suite = loads_suite(
            "cases:\n  - name: a\n    inputs: {n: x}\n"
            "    assert:\n      - judge: Is this rude?\n"
        )
        result = run_suite(
            prompt, suite, Echo(), judge_engine=Echo("FAIL, it is polite")
        )

        assert not result.ok


class TestReporting:
    @pytest.fixture
    def result(self, prompt: Prompt) -> SuiteResult:
        suite = loads_suite(
            "cases:\n"
            "  - name: ok\n    inputs: {n: Alice}\n"
            "    assert:\n      - contains: Alice\n"
            "  - name: bad\n    inputs: {n: Alice}\n"
            "    assert:\n      - contains: Bob\n"
            "  - name: later\n    skip: true\n    inputs: {n: x}\n"
        )

        return run_suite(prompt, suite, Echo())

    def test_dict_shape(self, result: SuiteResult) -> None:
        payload = to_dict(result)

        assert payload["passed"] == 1
        assert payload["failed"] == 1
        assert payload["skipped"] == 1
        cases = payload["cases"]

        assert isinstance(cases, list)
        assert len(cases) == 3

    def test_json_is_parseable(self, result: SuiteResult) -> None:
        assert json.loads(to_json(result))["prompt"] == "greet"

    def test_junit_is_valid_xml(self, result: SuiteResult) -> None:
        root = fromstring(to_junit(result))

        assert root.tag == "testsuite"
        assert root.attrib["tests"] == "3"
        assert root.attrib["failures"] == "1"

    def test_junit_marks_failures_and_skips(self, result: SuiteResult) -> None:
        root = fromstring(to_junit(result))
        kinds = {
            case.attrib["name"]: [child.tag for child in case]
            for case in root.findall("testcase")
        }

        assert kinds["ok"] == []
        assert kinds["bad"] == ["failure"]
        assert kinds["later"] == ["skipped"]

    def test_terminal_output(self, result: SuiteResult) -> None:
        from rich.console import Console

        console = Console(record=True, width=120)
        to_terminal(result, console)
        text = console.export_text()

        assert "1 passed, 1 failed, 1 skipped" in text
