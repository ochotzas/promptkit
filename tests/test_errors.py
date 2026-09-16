from __future__ import annotations

from pathlib import Path

import jinja2
import pydantic
import pytest
import yaml

from promptkit.core.loader import load_prompt
from promptkit.core.prompt import Prompt
from promptkit.core.schema import parse_type_string, validate_inputs
from promptkit.errors import (
    InputValidationError,
    PromptKitError,
    PromptNotFoundError,
    PromptParseError,
    SchemaError,
    TemplateError,
)


class TestHierarchy:
    def test_all_errors_share_a_base(self) -> None:
        for error in (
            PromptNotFoundError,
            PromptParseError,
            SchemaError,
            TemplateError,
            InputValidationError,
        ):
            assert issubclass(error, PromptKitError)

    def test_not_found_is_file_not_found(self) -> None:
        assert issubclass(PromptNotFoundError, FileNotFoundError)

    def test_parse_error_is_yaml_error(self) -> None:
        assert issubclass(PromptParseError, yaml.YAMLError)

    def test_template_error_is_jinja_error(self) -> None:
        assert issubclass(TemplateError, jinja2.TemplateError)

    def test_schema_error_is_value_error(self) -> None:
        assert issubclass(SchemaError, ValueError)

    def test_validation_error_is_value_error(self) -> None:
        assert issubclass(InputValidationError, ValueError)


class TestRaiseSites:
    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(PromptNotFoundError) as exc:
            load_prompt(tmp_path / "nope.yaml")

        assert "nope.yaml" in exc.value.path

    def test_malformed_yaml(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text("name: [unclosed\n")

        with pytest.raises(PromptParseError):
            load_prompt(path)

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        path = tmp_path / "partial.yaml"
        path.write_text("name: only_a_name\n")

        with pytest.raises(PromptParseError) as exc:
            load_prompt(path)

        assert set(exc.value.missing_fields) == {"description", "template"}

    def test_non_mapping_yaml(self, tmp_path: Path) -> None:
        path = tmp_path / "list.yaml"
        path.write_text("- a\n- b\n")

        with pytest.raises(PromptParseError):
            load_prompt(path)

    def test_non_mapping_input_schema(self, tmp_path: Path) -> None:
        path = tmp_path / "schema.yaml"
        path.write_text("name: n\ndescription: d\ntemplate: t\ninput_schema: [a]\n")

        with pytest.raises(PromptParseError):
            load_prompt(path)

    def test_unsupported_type_names_the_field(self) -> None:
        with pytest.raises(SchemaError) as exc:
            parse_type_string("set", field="tags")

        assert exc.value.field == "tags"
        assert "tags" in str(exc.value)

    def test_input_validation_error_exposes_pydantic_errors(self) -> None:
        with pytest.raises(InputValidationError) as exc:
            validate_inputs({}, {"name": "str"})

        assert len(exc.value.errors()) == 1
        assert isinstance(exc.value.cause, pydantic.ValidationError)

    def test_undefined_template_variable(self) -> None:
        prompt = Prompt(name="n", description="d", template="Hi {{ missing }}")

        with pytest.raises(TemplateError):
            prompt.render({}, validate=False)
