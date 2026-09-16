from __future__ import annotations

from pathlib import Path

import pytest

pytest_plugins = ["pytester"]

PROMPT = """name: greet
description: Greets a customer by name
version: 1.0.0
messages:
  - role: system
    template: Be brief.
  - role: user
    template: "Say hello to {{ name }}."
input_schema:
  name: str
"""

SUITE = """cases:
  - name: uses_the_name
    inputs: {name: Alice}
    assert:
      - contains: Alice
"""

RECORDER = """
from promptkit.core.loader import load_prompt
from promptkit.engines.base import BaseEngine
from promptkit.evals.case import load_suite
from promptkit.evals.cassette import Cassette, CassetteEngine, cassette_path_for
from promptkit.evals.runner import run_suite
from promptkit.types import Completion, Usage


class Fake(BaseEngine):
    def _complete(self, messages, **options):
        who = messages[-1].content.split()[-1].rstrip(".")
        return Completion(
            text=f"Hello {who}!", model="gpt-4o-mini", usage=Usage(10, 4)
        )


prompt = load_prompt("greet.yaml")
suite = load_suite("greet.evals.yaml")
cassette = Cassette.load(cassette_path_for("greet.evals.yaml"))
run_suite(prompt, suite, CassetteEngine(Fake("gpt-4o-mini"), cassette, mode="record"))
cassette.save()
"""


def write_suite(pytester: pytest.Pytester) -> None:
    pytester.makefile(".yaml", greet=PROMPT)
    (pytester.path / "greet.evals.yaml").write_text(SUITE)


def record(pytester: pytest.Pytester) -> None:
    (pytester.path / "record_it.py").write_text(RECORDER)
    result = pytester.run("python", "record_it.py")

    assert result.ret == 0


class TestCollection:
    def test_eval_suites_are_collected_as_tests(
        self, pytester: pytest.Pytester
    ) -> None:
        write_suite(pytester)
        result = pytester.runpytest("--collect-only", "-q")

        result.stdout.fnmatch_lines(["*greet.evals.yaml::uses_the_name*"])

    def test_collection_can_be_disabled(self, pytester: pytest.Pytester) -> None:
        write_suite(pytester)
        pytester.makeini("[pytest]\npromptkit_evals = false\n")
        result = pytester.runpytest("--collect-only", "-q")

        assert "uses_the_name" not in result.stdout.str()

    def test_ordinary_yaml_is_not_collected(self, pytester: pytest.Pytester) -> None:
        pytester.makefile(".yaml", config="key: value\n")
        result = pytester.runpytest("--collect-only", "-q")

        assert "config.yaml" not in result.stdout.str()


class TestRunning:
    def test_skips_cleanly_without_a_cassette(self, pytester: pytest.Pytester) -> None:
        write_suite(pytester)
        result = pytester.runpytest("-q")

        result.assert_outcomes(skipped=1)

    def test_passes_offline_from_a_cassette(self, pytester: pytest.Pytester) -> None:
        write_suite(pytester)
        record(pytester)
        result = pytester.runpytest("-q")

        result.assert_outcomes(passed=1)

    def test_a_failing_assertion_fails_the_test(
        self, pytester: pytest.Pytester
    ) -> None:
        write_suite(pytester)
        record(pytester)
        (pytester.path / "greet.evals.yaml").write_text(
            "cases:\n  - name: uses_the_name\n    inputs: {name: Alice}\n"
            "    assert:\n      - contains: Bob\n"
        )
        result = pytester.runpytest("-q")

        result.assert_outcomes(failed=1)
        result.stdout.fnmatch_lines(["*contains*"])

    def test_editing_the_prompt_reports_a_stale_cassette(
        self, pytester: pytest.Pytester
    ) -> None:
        write_suite(pytester)
        record(pytester)
        (pytester.path / "greet.yaml").write_text(
            PROMPT.replace("Say hello to {{ name }}.", "Greet {{ name }} warmly.")
        )
        result = pytester.runpytest("-q")

        result.assert_outcomes(failed=1)
        result.stdout.fnmatch_lines(["*changed since it was recorded*"])

    def test_skipped_cases_are_skipped(self, pytester: pytest.Pytester) -> None:
        pytester.makefile(".yaml", greet=PROMPT)
        (pytester.path / "greet.evals.yaml").write_text(
            "cases:\n  - name: later\n    skip: true\n    inputs: {name: A}\n"
        )
        result = pytester.runpytest("-q")

        result.assert_outcomes(skipped=1)

    def test_missing_prompt_file_is_a_usage_error(
        self, pytester: pytest.Pytester
    ) -> None:
        (pytester.path / "orphan.evals.yaml").write_text(SUITE)
        result = pytester.runpytest("-q")

        assert result.ret != 0
        assert "No prompt file found" in result.stdout.str()


class TestNoNetwork:
    def test_replay_makes_no_network_call(self, pytester: pytest.Pytester) -> None:
        write_suite(pytester)
        record(pytester)
        (pytester.path / "conftest.py").write_text(
            "import socket\n"
            "import pytest\n\n"
            "@pytest.fixture(autouse=True)\n"
            "def _block(monkeypatch):\n"
            "    def boom(*a, **k):\n"
            "        raise AssertionError('network call attempted')\n"
            "    monkeypatch.setattr(socket.socket, 'connect', boom)\n"
        )
        result = pytester.runpytest("-q")

        result.assert_outcomes(passed=1)


def test_plugin_is_registered(pytestconfig: pytest.Config) -> None:
    assert pytestconfig.pluginmanager.hasplugin("promptkit")


def test_cassette_is_written_next_to_the_suite(tmp_path: Path) -> None:
    from promptkit.evals.cassette import cassette_path_for

    suite = tmp_path / "greet.evals.yaml"

    assert cassette_path_for(suite).parent == tmp_path
