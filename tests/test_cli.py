from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from promptkit.cli.main import app
from promptkit.cli.vars import coerce, coerce_to, parse_pairs

runner = CliRunner()

PROMPT = """
name: greet
description: Greets someone
version: 1.0.0
messages:
  - role: system
    template: Be brief.
  - role: user
    template: "Hello {{ name }}, you are {{ age }} years old."
input_schema:
  name: str
  age: int
"""

EVALS = """
cases:
  - name: mentions_the_name
    inputs: {name: Alice, age: 30}
    assert:
      - contains: Alice
"""


@pytest.fixture
def prompt_file(tmp_path: Path) -> Path:
    path = tmp_path / "greet.yaml"
    path.write_text(PROMPT)

    return path


@pytest.fixture
def suite_file(prompt_file: Path) -> Path:
    path = prompt_file.with_name("greet.evals.yaml")
    path.write_text(EVALS)

    return path


class TestApp:
    def test_root_help_lists_every_command(self) -> None:
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        for command in (
            "run",
            "render",
            "lint",
            "info",
            "cost",
            "test",
            "diff",
            "list",
            "init",
            "engines",
        ):
            assert command in result.stdout

    @pytest.mark.parametrize(
        "command",
        [
            "run",
            "render",
            "lint",
            "info",
            "cost",
            "test",
            "diff",
            "list",
            "init",
            "engines",
        ],
    )
    def test_each_command_has_help(self, command: str) -> None:
        result = runner.invoke(app, [command, "--help"])

        assert result.exit_code == 0
        assert "Usage" in result.stdout

    def test_version(self) -> None:
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "PromptKit version" in result.stdout


class TestVariableInput:
    def test_set_pairs(self, prompt_file: Path) -> None:
        result = runner.invoke(
            app, ["render", str(prompt_file), "--set", "name=Alice", "--set", "age=30"]
        )

        assert result.exit_code == 0
        assert "Hello Alice, you are 30 years old." in result.stdout

    def test_set_is_schema_aware(self) -> None:
        assert coerce_to("9.99", "str") == "9.99"
        assert coerce_to("30", "int") == 30
        assert coerce_to("1.5", "float") == 1.5
        assert coerce_to("yes", "bool") is True
        assert coerce_to('["a"]', "list") == ["a"]

    def test_set_rejects_a_bad_number(self, prompt_file: Path) -> None:
        result = runner.invoke(
            app, ["render", str(prompt_file), "--set", "name=A", "--set", "age=old"]
        )

        assert result.exit_code != 0

    def test_set_without_equals_is_rejected(self, prompt_file: Path) -> None:
        result = runner.invoke(app, ["render", str(prompt_file), "--set", "oops"])

        assert result.exit_code != 0

    def test_value_containing_equals_is_preserved(self) -> None:
        assert parse_pairs(["q=a=b"]) == {"q": "a=b"}

    def test_vars_json(self, prompt_file: Path) -> None:
        result = runner.invoke(
            app,
            ["render", str(prompt_file), "--vars", '{"name": "Bob", "age": 44}'],
        )

        assert result.exit_code == 0
        assert "Hello Bob, you are 44 years old." in result.stdout

    def test_invalid_vars_json(self, prompt_file: Path) -> None:
        result = runner.invoke(app, ["render", str(prompt_file), "--vars", "{oops"])

        assert result.exit_code != 0

    def test_vars_file_yaml(self, prompt_file: Path, tmp_path: Path) -> None:
        values = tmp_path / "values.yaml"
        values.write_text("name: Carol\nage: 51\n")
        result = runner.invoke(
            app, ["render", str(prompt_file), "--vars-file", str(values)]
        )

        assert result.exit_code == 0
        assert "Carol" in result.stdout

    def test_vars_file_json(self, prompt_file: Path, tmp_path: Path) -> None:
        values = tmp_path / "values.json"
        values.write_text(json.dumps({"name": "Dana", "age": 22}))
        result = runner.invoke(
            app, ["render", str(prompt_file), "--vars-file", str(values)]
        )

        assert result.exit_code == 0
        assert "Dana" in result.stdout

    def test_missing_vars_file(self, prompt_file: Path, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["render", str(prompt_file), "--vars-file", str(tmp_path / "nope.yaml")],
        )

        assert result.exit_code != 0

    def test_set_overrides_vars(self, prompt_file: Path) -> None:
        result = runner.invoke(
            app,
            [
                "render",
                str(prompt_file),
                "--vars",
                '{"name": "Bob", "age": 1}',
                "--set",
                "name=Override",
            ],
        )

        assert result.exit_code == 0
        assert "Override" in result.stdout

    def test_placeholders_fill_missing_inputs(self, prompt_file: Path) -> None:
        result = runner.invoke(app, ["render", str(prompt_file)])

        assert result.exit_code == 0
        assert "placeholder" in result.stdout

    def test_interactive_asks_once_per_field(self, prompt_file: Path) -> None:
        result = runner.invoke(
            app, ["render", str(prompt_file), "--interactive"], input="Bob\n42\n"
        )

        assert result.exit_code == 0
        assert result.stdout.count("Enter value for 'name'") == 1
        assert "Hello Bob, you are 42 years old." in result.stdout

    def test_legacy_name_flag_is_removed(self, prompt_file: Path) -> None:
        result = runner.invoke(
            app, ["render", str(prompt_file), "--name", "Legacy", "--set", "age=1"]
        )

        assert result.exit_code != 0

    def test_coerce_guesses_without_a_schema(self) -> None:
        assert coerce("3") == 3
        assert coerce("true") is True
        assert coerce("null") is None
        assert coerce("plain") == "plain"


class TestRender:
    def test_messages_flag_shows_roles(self, prompt_file: Path) -> None:
        result = runner.invoke(
            app,
            [
                "render",
                str(prompt_file),
                "--set",
                "name=A",
                "--set",
                "age=1",
                "--messages",
            ],
        )

        assert result.exit_code == 0
        assert "system" in result.stdout
        assert "user" in result.stdout

    def test_output_file(self, prompt_file: Path, tmp_path: Path) -> None:
        out = tmp_path / "rendered.txt"
        result = runner.invoke(
            app,
            [
                "render",
                str(prompt_file),
                "--set",
                "name=A",
                "--set",
                "age=1",
                "--output",
                str(out),
            ],
        )

        assert result.exit_code == 0
        assert "Hello A" in out.read_text()

    def test_missing_file(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["render", str(tmp_path / "nope.yaml")])

        assert result.exit_code == 1


class TestLint:
    def test_clean_prompt_passes(self, prompt_file: Path) -> None:
        result = runner.invoke(app, ["lint", str(prompt_file)])

        assert result.exit_code == 0

    def test_error_fails(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("name: b\ndescription: d\ntemplate: Hi {{ undeclared }}\n")
        result = runner.invoke(app, ["lint", str(bad)])

        assert result.exit_code == 1
        assert "PK001" in result.stdout

    def test_strict_promotes_warnings(self, tmp_path: Path) -> None:
        warn = tmp_path / "warn.yaml"
        warn.write_text(
            "name: w\ndescription: d\nversion: 1.0.0\ntemplate: Hi\n"
            "input_schema: {unused: str}\n"
        )

        assert runner.invoke(app, ["lint", str(warn)]).exit_code == 0
        assert runner.invoke(app, ["lint", str(warn), "--strict"]).exit_code == 1

    def test_json_format(self, prompt_file: Path) -> None:
        result = runner.invoke(app, ["lint", str(prompt_file), "--format", "json"])

        assert result.exit_code == 0
        assert "fingerprint" in result.stdout

    def test_rules_listing(self) -> None:
        result = runner.invoke(app, ["lint", "x", "--rules"])

        assert result.exit_code == 0
        assert "PK001" in result.stdout

    def test_directory_target(self, prompt_file: Path) -> None:
        result = runner.invoke(app, ["lint", str(prompt_file.parent)])

        assert result.exit_code == 0


class TestInfoAndList:
    def test_info(self, prompt_file: Path) -> None:
        result = runner.invoke(app, ["info", str(prompt_file)])

        assert result.exit_code == 0
        assert "greet" in result.stdout
        assert "system" in result.stdout

    def test_list(self, prompt_file: Path) -> None:
        result = runner.invoke(app, ["list", str(prompt_file.parent)])

        assert result.exit_code == 0
        assert "greet" in result.stdout

    def test_list_empty_directory(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["list", str(tmp_path)])

        assert result.exit_code == 0
        assert "No prompts" in result.stdout

    def test_list_counts_eval_cases(self, suite_file: Path) -> None:
        result = runner.invoke(app, ["list", str(suite_file.parent)])

        assert result.exit_code == 0


class TestCost:
    def test_known_model(self, prompt_file: Path) -> None:
        result = runner.invoke(
            app, ["cost", str(prompt_file), "--model", "gpt-4o-mini"]
        )

        assert result.exit_code == 0
        assert "$" in result.stdout

    def test_unknown_model(self, prompt_file: Path) -> None:
        result = runner.invoke(app, ["cost", str(prompt_file), "--model", "nope-9000"])

        assert result.exit_code == 0
        assert "No pricing" in result.stdout

    def test_model_listing(self) -> None:
        result = runner.invoke(app, ["cost", "--models"])

        assert result.exit_code == 0
        assert "gpt-4o-mini" in result.stdout


class TestDiff:
    def test_identical(self, prompt_file: Path, tmp_path: Path) -> None:
        copy = tmp_path / "copy.yaml"
        copy.write_text(prompt_file.read_text())
        result = runner.invoke(app, ["diff", str(prompt_file), str(copy)])

        assert result.exit_code == 0
        assert "identical" in result.stdout

    def test_changed_exits_nonzero(self, prompt_file: Path, tmp_path: Path) -> None:
        other = tmp_path / "other.yaml"
        other.write_text(prompt_file.read_text().replace("Be brief.", "Be verbose."))
        result = runner.invoke(app, ["diff", str(prompt_file), str(other)])

        assert result.exit_code == 1
        assert "Be verbose." in result.stdout


class TestInit:
    def test_creates_a_prompt(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["init", "hello", "--dir", str(tmp_path)])

        assert result.exit_code == 0
        assert (tmp_path / "hello.yaml").is_file()

    def test_scaffold_passes_lint(self, tmp_path: Path) -> None:
        runner.invoke(app, ["init", "hello", "--dir", str(tmp_path), "--messages"])
        result = runner.invoke(app, ["lint", str(tmp_path / "hello.yaml")])

        assert result.exit_code == 0

    def test_evals_scaffold(self, tmp_path: Path) -> None:
        runner.invoke(app, ["init", "hello", "--dir", str(tmp_path), "--evals"])

        assert (tmp_path / "hello.evals.yaml").is_file()

    def test_nested_name(self, tmp_path: Path) -> None:
        runner.invoke(app, ["init", "support/refund", "--dir", str(tmp_path)])

        assert (tmp_path / "support" / "refund.yaml").is_file()

    def test_refuses_to_overwrite(self, tmp_path: Path) -> None:
        runner.invoke(app, ["init", "hello", "--dir", str(tmp_path)])
        result = runner.invoke(app, ["init", "hello", "--dir", str(tmp_path)])

        assert result.exit_code == 1

    def test_force_overwrites(self, tmp_path: Path) -> None:
        runner.invoke(app, ["init", "hello", "--dir", str(tmp_path)])
        result = runner.invoke(
            app, ["init", "hello", "--dir", str(tmp_path), "--force"]
        )

        assert result.exit_code == 0


class TestEngines:
    def test_lists_every_builtin(self) -> None:
        result = runner.invoke(app, ["engines"])

        assert result.exit_code == 0
        for name in ("openai", "anthropic", "ollama", "compatible"):
            assert name in result.stdout

    def test_install_hint_survives_rich_markup(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from promptkit.engines import plugins

        monkeypatch.setattr(
            plugins,
            "discover",
            lambda: {
                "openai": plugins.EngineInfo("openai", "t", "openai", installed=False)
            },
        )
        result = runner.invoke(app, ["engines"])

        assert result.exit_code == 0
        assert "[openai]" in result.stdout


class TestRunCommand:
    def test_unknown_engine_is_reported(self, prompt_file: Path) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                str(prompt_file),
                "--engine",
                "nope",
                "--set",
                "name=A",
                "--set",
                "age=1",
            ],
        )

        assert result.exit_code == 1

    def test_engine_resolves_through_plugins(
        self, prompt_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from promptkit.engines.base import BaseEngine
        from promptkit.types import Completion, Message, Usage

        class Echo(BaseEngine):
            def __init__(self, **kw: Any) -> None:
                super().__init__("echo")

            def _complete(self, messages: list[Message], **options: Any) -> Completion:
                return Completion(text="echoed", model=self.model, usage=Usage(1, 1))

        from promptkit.engines import plugins

        monkeypatch.setattr(plugins, "load", lambda name: Echo)
        result = runner.invoke(
            app, ["run", str(prompt_file), "--set", "name=A", "--set", "age=1"]
        )

        assert result.exit_code == 0
        assert "echoed" in result.stdout


class TestTestCommand:
    def test_no_suite_is_reported(self, prompt_file: Path) -> None:
        result = runner.invoke(app, ["test", str(prompt_file)])

        assert result.exit_code == 1
        assert "No eval suites" in result.stdout

    def test_suite_runs_against_a_stub_engine(
        self, suite_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from promptkit.engines.base import BaseEngine
        from promptkit.types import Completion, Message, Usage

        class Echo(BaseEngine):
            def __init__(self, **kw: Any) -> None:
                super().__init__("echo")

            def _complete(self, messages: list[Message], **options: Any) -> Completion:
                return Completion(
                    text="Hello Alice", model=self.model, usage=Usage(1, 1)
                )

        from promptkit.engines import plugins

        monkeypatch.setattr(plugins, "load", lambda name: Echo)
        result = runner.invoke(app, ["test", str(suite_file.with_name("greet.yaml"))])

        assert result.exit_code == 0
        assert "1 passed" in result.stdout
