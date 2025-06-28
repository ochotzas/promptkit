"""
Unit tests for PromptKit core functionality.

This module contains comprehensive tests for the Prompt class,
schema validation, template rendering, and related functionality.
"""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from promptkit.core.compiler import PromptCompiler
from promptkit.core.loader import load_prompt, save_prompt
from promptkit.core.prompt import Prompt
from promptkit.core.runner import run_prompt
from promptkit.core.schema import create_schema_model, validate_inputs
from promptkit.engines.base import BaseEngine
from promptkit.utils.tokens import estimate_cost, estimate_tokens


class MockEngine(BaseEngine):
    """Mock engine for testing."""

    def __init__(self, response: str = "Mock response"):
        super().__init__("mock")
        self.response = response

    def generate(self, prompt: str) -> str:
        return self.response


class TestPrompt:
    """Test cases for the Prompt class."""

    def test_prompt_creation(self) -> None:
        """Test basic prompt creation."""
        prompt = Prompt(
            name="test_prompt",
            description="A test prompt",
            template="Hello {{ name }}!",
            input_schema={"name": "str"},
        )

        assert prompt.name == "test_prompt"
        assert prompt.description == "A test prompt"
        assert prompt.template == "Hello {{ name }}!"
        assert prompt.input_schema == {"name": "str"}

    def test_prompt_rendering(self) -> None:
        """Test prompt template rendering."""
        prompt = Prompt(
            name="greet",
            description="Greeting prompt",
            template="Hello {{ name }}, you are {{ age }} years old!",
            input_schema={"name": "str", "age": "int"},
        )

        result = prompt.render({"name": "Alice", "age": 30})
        assert result == "Hello Alice, you are 30 years old!"

    def test_prompt_validation_success(self) -> None:
        """Test successful input validation."""
        prompt = Prompt(
            name="test",
            description="Test",
            template="Hello {{ name }}!",
            input_schema={"name": "str"},
        )

        validated = prompt.validate_inputs({"name": "Alice"})
        assert validated == {"name": "Alice"}

    def test_prompt_validation_failure(self) -> None:
        """Test input validation failure."""
        prompt = Prompt(
            name="test",
            description="Test",
            template="Hello {{ name }}!",
            input_schema={"name": "str"},
        )

        with pytest.raises(Exception):  # ValidationError
            prompt.validate_inputs({})  # Missing required field

    def test_get_required_inputs(self) -> None:
        """Test getting required input fields."""
        prompt = Prompt(
            name="test",
            description="Test",
            template="Hello {{ name }}, email: {{ email }}!",
            input_schema={"name": "str", "email": "str | None"},
        )

        required = prompt.get_required_inputs()
        optional = prompt.get_optional_inputs()

        assert "name" in required
        assert "email" in optional
        assert len(required) == 1
        assert len(optional) == 1


class TestSchema:
    """Test cases for schema validation."""

    def test_create_schema_model(self) -> None:
        """Test creating Pydantic model from schema."""
        schema = {"name": "str", "age": "int"}
        Model = create_schema_model(schema)

        instance = Model(name="Alice", age=30)
        assert instance.name == "Alice"  # type: ignore[attr-defined]
        assert instance.age == 30  # type: ignore[attr-defined]

    def test_validate_inputs_success(self) -> None:
        """Test successful input validation."""
        schema = {"name": "str", "age": "int"}
        inputs = {"name": "Alice", "age": 30}

        validated = validate_inputs(inputs, schema)
        assert validated == inputs

    def test_validate_inputs_optional(self) -> None:
        """Test validation with optional fields."""
        schema = {"name": "str", "email": "str | None"}
        inputs = {"name": "Alice"}

        validated = validate_inputs(inputs, schema)
        assert validated["name"] == "Alice"
        # email should be None or not present

    def test_empty_schema(self) -> None:
        """Test validation with empty schema."""
        inputs = {"anything": "value"}
        validated = validate_inputs(inputs, {})
        assert validated == inputs


class TestCompiler:
    """Test cases for template compilation."""

    def test_compile_template(self) -> None:
        """Test template compilation."""
        compiler = PromptCompiler()
        template = compiler.compile_template("Hello {{ name }}!")

        result = compiler.render_template(template, {"name": "Alice"})
        assert result == "Hello Alice!"

    def test_render_string(self) -> None:
        """Test direct string rendering."""
        compiler = PromptCompiler()
        result = compiler.render_string("Hello {{ name }}!", {"name": "Alice"})
        assert result == "Hello Alice!"

    def test_undefined_variable(self) -> None:
        """Test handling of undefined variables."""
        compiler = PromptCompiler()

        with pytest.raises(Exception):  # TemplateError
            compiler.render_string("Hello {{ undefined }}!", {})


class TestLoader:
    """Test cases for prompt loading and saving."""

    def test_save_and_load_prompt(self) -> None:
        """Test saving and loading a prompt."""
        original_prompt = Prompt(
            name="test_prompt",
            description="A test prompt",
            template="Hello {{ name }}!",
            input_schema={"name": "str"},
        )

        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_path = Path(f.name)

        try:
            save_prompt(original_prompt, temp_path)
            loaded_prompt = load_prompt(temp_path)

            assert loaded_prompt.name == original_prompt.name
            assert loaded_prompt.description == original_prompt.description
            assert loaded_prompt.template == original_prompt.template
            assert loaded_prompt.input_schema == original_prompt.input_schema

        finally:
            temp_path.unlink()

    def test_load_nonexistent_file(self) -> None:
        """Test loading a non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent.yaml")

    def test_load_without_extension(self) -> None:
        """Test loading a prompt file without specifying the .yaml extension."""
        # Create a temporary prompt file
        prompt = Prompt(
            name="test_no_ext",
            description="Test prompt for extension-optional loading",
            template="Hello {{ name }}!",
            input_schema={"name": "str"},
        )

        temp_path = Path("test_no_ext.yaml")
        try:
            save_prompt(prompt, temp_path)

            # Load with extension
            prompt_with_ext = load_prompt("test_no_ext.yaml")

            # Load without extension
            prompt_without_ext = load_prompt("test_no_ext")

            # Both should be identical
            assert prompt_with_ext.name == prompt_without_ext.name
            assert prompt_with_ext.template == prompt_without_ext.template
            assert prompt_with_ext.description == prompt_without_ext.description
            assert prompt_with_ext.input_schema == prompt_without_ext.input_schema

        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestRunner:
    """Test cases for prompt execution."""

    def test_run_prompt_success(self) -> None:
        """Test successful prompt execution."""
        prompt = Prompt(
            name="test",
            description="Test",
            template="Hello {{ name }}!",
            input_schema={"name": "str"},
        )

        engine = MockEngine("Generated response")
        result = run_prompt(prompt, {"name": "Alice"}, engine)

        assert result == "Generated response"

    def test_run_prompt_validation_error(self) -> None:
        """Test prompt execution with validation error."""
        prompt = Prompt(
            name="test",
            description="Test",
            template="Hello {{ name }}!",
            input_schema={"name": "str"},
        )

        engine = MockEngine()

        with pytest.raises(Exception):  # ValidationError
            run_prompt(prompt, {}, engine)  # Missing required input


class TestTokens:
    """Test cases for token estimation and cost calculation."""

    def test_estimate_tokens(self) -> None:
        """Test token estimation."""
        text = "Hello, world! This is a test."
        tokens = estimate_tokens(text)

        assert tokens > 0
        assert isinstance(tokens, int)

    def test_estimate_tokens_empty(self) -> None:
        """Test token estimation with empty string."""
        assert estimate_tokens("") == 0

    def test_estimate_cost(self) -> None:
        """Test cost estimation."""
        cost = estimate_cost(1000, 500, "gpt-4o-mini")

        assert cost is not None
        assert cost > 0
        assert isinstance(cost, float)

    def test_estimate_cost_unknown_model(self) -> None:
        """Test cost estimation with unknown model."""
        cost = estimate_cost(1000, 500, "unknown-model")
        assert cost is None


# Integration tests
class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_workflow(self) -> None:
        """Test the complete workflow from YAML to response."""
        # Create a temporary YAML file
        yaml_content = """
name: integration_test
description: Integration test prompt
template: |
  Hello {{ name }}! You are {{ age }} years old.
  {% if email %}Your email is {{ email }}.{% endif %}
input_schema:
  name: str
  age: int
  email: "str | None"
"""

        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            # Load prompt
            prompt = load_prompt(temp_path)

            # Prepare inputs
            inputs = {"name": "Alice", "age": 30, "email": "alice@example.com"}

            # Create mock engine
            engine = MockEngine("Integration test response")

            # Run prompt
            result = run_prompt(prompt, inputs, engine)

            assert result == "Integration test response"

        finally:
            temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__])
