from __future__ import annotations

from pathlib import Path

import pytest

from promptkit.core.lint import (
    RULES,
    declared_fields,
    has_errors,
    lint_prompt,
    template_variables,
    to_dict,
    worst_severity,
)
from promptkit.core.loader import load_prompt
from promptkit.core.prompt import Prompt
from promptkit.core.registry import is_eval_suite


def codes(prompt: Prompt, root: str | Path | None = None) -> set[str]:
    return {f.code for f in lint_prompt(prompt, root)}


class TestRules:
    def test_every_rule_has_a_known_severity(self) -> None:
        assert all(r.severity in ("error", "warning", "info") for r in RULES.values())

    def test_codes_are_unique_and_sorted(self) -> None:
        assert list(RULES) == sorted(RULES)


class TestFindings:
    def test_undeclared_variable_is_an_error(self) -> None:
        prompt = Prompt(name="n", description="d", template="Hi {{ who }}")

        assert "PK001" in codes(prompt)
        assert has_errors(lint_prompt(prompt))

    def test_unused_schema_field_is_a_warning(self) -> None:
        prompt = Prompt(
            name="n",
            description="d",
            template="Hi {{ a }}",
            input_schema={"a": "str", "b": "str"},
        )
        findings = {f.code: f for f in lint_prompt(prompt)}

        assert findings["PK002"].field == "b"
        assert findings["PK002"].severity == "warning"

    def test_unresolved_include_is_an_error(self, tmp_path: Path) -> None:
        (tmp_path / "p.yaml").write_text(
            "name: p\ndescription: d\ntemplate: \"{% include 'missing.j2' %}\"\n"
        )
        prompt = Prompt(
            name="p",
            description="d",
            template="{% include 'missing.j2' %}",
            template_root=str(tmp_path),
        )

        assert "PK003" in codes(prompt, tmp_path)

    def test_broken_template_is_an_error_and_stops_there(self) -> None:
        broken = Prompt(name="n", description="d", template="{% for %}")
        findings = lint_prompt(broken)

        assert [f.code for f in findings] == ["PK004"]

    def test_missing_description_is_a_warning(self) -> None:
        assert "PK005" in codes(Prompt(name="n", description="  ", template="hi"))

    def test_no_system_message_is_info(self) -> None:
        assert "PK006" in codes(Prompt(name="n", description="d", template="hi"))

    def test_system_message_clears_the_rule(self) -> None:
        prompt = Prompt(
            name="n",
            description="d",
            messages=[
                {"role": "system", "template": "S"},
                {"role": "user", "template": "U"},
            ],
        )

        assert "PK006" not in codes(prompt)

    def test_default_version_is_info(self) -> None:
        assert "PK007" in codes(Prompt(name="n", description="d", template="hi"))

    def test_pinned_version_clears_the_rule(self) -> None:
        prompt = Prompt(name="n", description="d", template="hi", version="1.2.0")

        assert "PK007" not in codes(prompt)

    def test_variables_without_schema_is_a_warning(self) -> None:
        assert "PK008" in codes(Prompt(name="n", description="d", template="{{ a }}"))

    def test_empty_message_is_a_warning(self) -> None:
        prompt = Prompt(
            name="n",
            description="d",
            messages=[
                {"role": "system", "template": "   "},
                {"role": "user", "template": "U"},
            ],
        )

        assert "PK009" in codes(prompt)

    def test_a_clean_prompt_has_only_info_findings(self) -> None:
        prompt = Prompt(
            name="n",
            description="A good description",
            version="1.0.0",
            messages=[
                {"role": "system", "template": "Be brief."},
                {"role": "user", "template": "Hi {{ who }}"},
            ],
            input_schema={"who": "str"},
        )

        assert lint_prompt(prompt) == []


class TestHelpers:
    def test_template_variables(self) -> None:
        prompt = Prompt(
            name="n", description="d", template="{{ a }} {% if b %}{{ c }}{% endif %}"
        )

        assert template_variables(prompt) == {"a", "b", "c"}

    def test_declared_fields_from_type_strings(self) -> None:
        prompt = Prompt(
            name="n", description="d", template="x", input_schema={"a": "str"}
        )

        assert declared_fields(prompt) == {"a"}

    def test_declared_fields_from_json_schema(self) -> None:
        prompt = Prompt(
            name="n",
            description="d",
            template="x",
            input_schema={
                "type": "object",
                "properties": {"a": {"type": "string"}},
            },
        )

        assert declared_fields(prompt) == {"a"}

    def test_worst_severity_ordering(self) -> None:
        prompt = Prompt(name="n", description="", template="{{ a }}")

        assert worst_severity(lint_prompt(prompt)) == "error"

    def test_worst_severity_of_nothing(self) -> None:
        assert worst_severity([]) is None

    def test_to_dict_includes_the_fingerprint(self) -> None:
        prompt = Prompt(name="n", description="d", template="hi")
        payload = to_dict(prompt, lint_prompt(prompt))

        assert payload["fingerprint"] == prompt.fingerprint
        assert isinstance(payload["findings"], list)


class TestShippedExamples:
    @pytest.mark.parametrize("name", ["support_reply", "structured_output"])
    def test_curated_examples_are_clean(self, name: str) -> None:
        prompt = load_prompt(Path("examples") / f"{name}.yaml")

        assert lint_prompt(prompt) == []

    def test_no_shipped_example_has_errors(self) -> None:
        for path in sorted(Path("examples").glob("*.yaml")):
            if is_eval_suite(path):
                continue

            assert not has_errors(lint_prompt(load_prompt(path))), path
