"""Core Prompt class."""

from typing import Any, Dict, Optional

from jinja2 import Template
from pydantic import BaseModel, ConfigDict, Field

from promptkit.core.compiler import PromptCompiler
from promptkit.core.schema import validate_inputs


class Prompt(BaseModel):
    """Prompt with template, schema, and metadata."""

    name: str = Field(..., description="Unique identifier for the prompt")
    description: str = Field(..., description="Human-readable description")
    template: str = Field(..., description="Jinja2 template string")
    input_schema: Dict[str, str] = Field(
        default_factory=dict, description="Input schema mapping field names to types"
    )

    # Private attributes
    _compiled_template: Optional[Template] = None
    _compiler: PromptCompiler = PromptCompiler()

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __post_init__(self) -> None:
        """Post-initialization to compile the template."""
        self._compile_template()

    def model_post_init(self, __context: Any) -> None:
        """Pydantic v2 post-init hook."""
        self._compile_template()

    def _compile_template(self) -> None:
        """Compile the Jinja2 template for efficient reuse."""
        self._compiled_template = self._compiler.compile_template(self.template)

    def validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate inputs against the prompt's schema."""
        return validate_inputs(inputs, self.input_schema)

    def render(self, inputs: Dict[str, Any], validate: bool = True) -> str:
        """Render the template with inputs."""
        if validate:
            inputs = self.validate_inputs(inputs)

        if self._compiled_template is None:
            self._compile_template()

        assert self._compiled_template is not None  # Type assertion for mypy
        return self._compiler.render_template(self._compiled_template, inputs)

    def get_required_inputs(self) -> list[str]:
        """Get required input field names."""
        return [
            field_name
            for field_name, type_str in self.input_schema.items()
            if " | None" not in type_str
        ]

    def get_optional_inputs(self) -> list[str]:
        """Get optional input field names."""
        return [
            field_name
            for field_name, type_str in self.input_schema.items()
            if " | None" in type_str
        ]
