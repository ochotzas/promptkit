from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import pytest

from promptkit.core.loader import load_prompt, loads_prompt, save_prompt
from promptkit.core.message import MessageTemplate, parse_messages
from promptkit.core.prompt import DEFAULT_VERSION, Prompt
from promptkit.core.registry import is_eval_suite
from promptkit.errors import PromptParseError, SchemaError

LEGACY = """
name: legacy
description: single template form
template: "Hello {{ name }}"
input_schema:
  name: str
"""

MODERN = """
name: modern
description: message form
version: 2.1.0
messages:
  - role: system
    template: "You are terse."
  - role: user
    template: "Hello {{ name }}"
input_schema:
  name: str
metadata:
  tags: [greeting, demo]
  author: Olger
  model: gpt-4o-mini
"""


class TestLegacyCompatibility:
    def test_template_kwarg_becomes_one_user_message(self) -> None:
        prompt = Prompt(name="n", description="d", template="Hi")

        assert len(prompt.messages) == 1
        assert prompt.messages[0].role == "user"
        assert prompt.messages[0].template == "Hi"

    def test_legacy_yaml_loads(self) -> None:
        prompt = loads_prompt(LEGACY)

        assert prompt.render({"name": "Ada"}) == "Hello Ada"

    def test_version_defaults(self) -> None:
        assert loads_prompt(LEGACY).version == DEFAULT_VERSION

    def test_template_property_is_removed(self) -> None:
        prompt = Prompt(name="n", description="d", template="Hi")

        assert not hasattr(prompt, "template")

    def test_joined_template_does_not_warn(self) -> None:
        prompt = Prompt(name="n", description="d", template="Hi")

        with warnings.catch_warnings():
            warnings.simplefilter("error")

            assert prompt.joined_template == "Hi"

    LEGACY_EXAMPLES = (
        "code_review",
        "greet_user",
        "meeting_summary",
        "product_description",
        "simple_demo",
    )

    def test_every_shipped_example_still_loads(self) -> None:
        examples = [
            p for p in sorted(Path("examples").glob("*.yaml")) if not is_eval_suite(p)
        ]

        assert examples

        for path in examples:
            assert load_prompt(path).messages

    @pytest.mark.parametrize("stem", LEGACY_EXAMPLES)
    def test_legacy_example_is_unchanged_in_shape(self, stem: str) -> None:
        prompt = load_prompt(Path("examples") / f"{stem}.yaml")

        assert prompt.version == DEFAULT_VERSION
        assert len(prompt.messages) == 1
        assert prompt.messages[0].role == "user"
        assert prompt.dependencies == ()


class TestMessages:
    def test_roles_preserved(self) -> None:
        prompt = loads_prompt(MODERN)

        assert [m.role for m in prompt.messages] == ["system", "user"]

    def test_render_messages_returns_typed_messages(self) -> None:
        messages = loads_prompt(MODERN).render_messages({"name": "Ada"})

        assert messages[0].role == "system"
        assert messages[1].content == "Hello Ada"

    def test_render_joins_messages(self) -> None:
        assert loads_prompt(MODERN).render({"name": "Ada"}) == (
            "You are terse.\n\nHello Ada"
        )

    def test_blank_messages_are_dropped(self) -> None:
        prompt = Prompt(
            name="n",
            description="d",
            messages=[
                {"role": "system", "template": "{{ preamble }}"},
                {"role": "user", "template": "Hi"},
            ],
            input_schema={"preamble": "str"},
        )

        assert len(prompt.render_messages({"preamble": "   "})) == 1

    def test_shorthand_role_mapping(self) -> None:
        templates = parse_messages([{"system": "S"}, {"user": "U"}])

        assert [(t.role, t.template) for t in templates] == [
            ("system", "S"),
            ("user", "U"),
        ]

    def test_bare_string_is_a_user_message(self) -> None:
        assert parse_messages(["hello"])[0].role == "user"

    def test_unknown_role_is_rejected(self) -> None:
        payload: dict[str, Any] = {"role": "wizard", "template": "x"}

        with pytest.raises(ValueError, match="unknown role"):
            MessageTemplate(**payload)

    def test_a_prompt_needs_content(self) -> None:
        with pytest.raises(ValueError, match="at least one message"):
            Prompt(name="n", description="d", messages=[])

    def test_yaml_without_content_is_rejected(self) -> None:
        with pytest.raises(PromptParseError) as exc:
            loads_prompt("name: n\ndescription: d\n")

        assert "template" in exc.value.missing_fields


class TestMetadata:
    def test_metadata_parsed(self) -> None:
        metadata = loads_prompt(MODERN).metadata

        assert metadata.tags == ("greeting", "demo")
        assert metadata.author == "Olger"
        assert metadata.model == "gpt-4o-mini"

    def test_metadata_defaults_are_empty(self) -> None:
        assert loads_prompt(LEGACY).metadata.tags == ()

    def test_metadata_does_not_change_rendering(self) -> None:
        with_meta = loads_prompt(MODERN)
        without = Prompt(
            name="modern",
            description="message form",
            messages=with_meta.messages,
            input_schema={"name": "str"},
        )

        assert with_meta.render({"name": "A"}) == without.render({"name": "A"})


class TestFingerprint:
    def test_stable_across_instances(self) -> None:
        assert loads_prompt(MODERN).fingerprint == loads_prompt(MODERN).fingerprint

    def test_changes_with_template(self) -> None:
        a = Prompt(name="n", description="d", template="A")
        b = Prompt(name="n", description="d", template="B")

        assert a.fingerprint != b.fingerprint

    def test_changes_with_role(self) -> None:
        a = Prompt(
            name="n", description="d", messages=[{"role": "user", "template": "X"}]
        )
        b = Prompt(
            name="n", description="d", messages=[{"role": "system", "template": "X"}]
        )

        assert a.fingerprint != b.fingerprint

    def test_changes_with_input_schema(self) -> None:
        a = Prompt(name="n", description="d", template="X", input_schema={"a": "str"})
        b = Prompt(name="n", description="d", template="X", input_schema={"a": "int"})

        assert a.fingerprint != b.fingerprint

    def test_version_is_advisory_not_identity(self) -> None:
        a = Prompt(name="n", description="d", template="X", version="1.0.0")
        b = Prompt(name="n", description="d", template="X", version="9.9.9")

        assert a.fingerprint == b.fingerprint

    def test_description_is_not_identity(self) -> None:
        a = Prompt(name="n", description="one", template="X")
        b = Prompt(name="n", description="two", template="X")

        assert a.fingerprint == b.fingerprint


class TestSchemaBoundary:
    def test_type_strings_still_work(self) -> None:
        prompt = Prompt(
            name="n", description="d", template="{{ a }}", input_schema={"a": "str"}
        )

        assert prompt.validate_inputs({"a": "x"}) == {"a": "x"}

    def test_type_string_language_is_frozen(self) -> None:
        prompt = Prompt(
            name="n",
            description="d",
            template="{{ a }}",
            input_schema={"a": "list[str]"},
        )

        with pytest.raises(SchemaError, match="frozen"):
            prompt.validate_inputs({"a": ["x"]})

    def test_frozen_error_names_the_field_and_suggests_json_schema(self) -> None:
        prompt = Prompt(
            name="n", description="d", template="{{ a }}", input_schema={"a": "set"}
        )

        with pytest.raises(SchemaError) as exc:
            prompt.validate_inputs({"a": 1})

        assert exc.value.field == "a"
        assert "JSON Schema" in str(exc.value)

    def test_json_schema_input_is_accepted(self) -> None:
        prompt = Prompt(
            name="n",
            description="d",
            template="{{ tags }}",
            input_schema={
                "type": "object",
                "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
                "required": ["tags"],
            },
        )

        assert prompt.validate_inputs({"tags": ["a", "b"]}) == {"tags": ["a", "b"]}
        assert prompt.get_required_inputs() == ["tags"]

    def test_output_schema_compiles_to_a_model(self) -> None:
        prompt = Prompt(
            name="n",
            description="d",
            template="x",
            output_schema={
                "type": "object",
                "properties": {"score": {"type": "integer"}},
                "required": ["score"],
            },
        )
        model = prompt.output_model()

        assert model is not None
        assert model(score=3).model_dump() == {"score": 3}

    def test_no_output_schema_means_no_model(self) -> None:
        assert Prompt(name="n", description="d", template="x").output_model() is None


class TestRoundTrip:
    def test_legacy_prompt_saves_as_template(self, tmp_path: Path) -> None:
        prompt = Prompt(name="n", description="d", template="Hi {{ a }}")
        path = tmp_path / "out.yaml"
        save_prompt(prompt, path)

        assert "template:" in path.read_text()
        assert load_prompt(path).joined_template == "Hi {{ a }}"

    def test_multi_message_prompt_saves_as_messages(self, tmp_path: Path) -> None:
        prompt = loads_prompt(MODERN)
        path = tmp_path / "out.yaml"
        save_prompt(prompt, path)

        assert "messages:" in path.read_text()

        reloaded = load_prompt(path)

        assert [m.role for m in reloaded.messages] == ["system", "user"]
        assert reloaded.fingerprint == prompt.fingerprint


class TestPublishedSchema:
    def test_schema_is_valid_json(self) -> None:
        import json

        schema = json.loads(
            Path("promptkit/schemas/prompt.schema.json").read_text(encoding="utf-8")
        )

        assert schema["$id"].endswith("/schemas/prompt.schema.json")
        assert set(schema["required"]) == {"name", "description"}

    def test_docs_copy_matches_the_packaged_schema(self) -> None:
        packaged = Path("promptkit/schemas/prompt.schema.json").read_text(
            encoding="utf-8"
        )
        published = Path("docs/schemas/prompt.schema.json").read_text(encoding="utf-8")

        assert packaged == published, (
            "docs/schemas/prompt.schema.json has drifted; "
            "copy promptkit/schemas/prompt.schema.json over it"
        )

    def test_schema_id_matches_the_docs_site(self) -> None:
        import json

        schema = json.loads(
            Path("promptkit/schemas/prompt.schema.json").read_text(encoding="utf-8")
        )
        site_url = "https://promptkit.ochotzas.com/"

        assert schema["$id"] == f"{site_url}schemas/prompt.schema.json"
