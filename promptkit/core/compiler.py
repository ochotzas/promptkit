"""
Jinja2 template compilation and rendering.

This module handles template compilation and rendering using Jinja2,
providing safe and efficient template processing for prompts.
"""

from typing import Any, Dict

from jinja2 import Environment, StrictUndefined, Template
from jinja2.exceptions import TemplateError


class PromptCompiler:
    """
    Handles Jinja2 template compilation and rendering for prompts.

    Uses StrictUndefined to ensure all template variables are provided,
    preventing silent failures from undefined variables.
    """

    def __init__(self) -> None:
        """Initialize the compiler with a strict Jinja2 environment."""
        self.env = Environment(
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def compile_template(self, template_str: str) -> Template:
        """
        Compile a template string into a Jinja2 Template object.

        Args:
            template_str: The template string to compile

        Returns:
            Compiled Jinja2 template

        Raises:
            TemplateError: If template compilation fails
        """
        try:
            return self.env.from_string(template_str)
        except TemplateError as e:
            raise TemplateError(f"Template compilation failed: {e}") from e

    def render_template(self, template: Template, variables: Dict[str, Any]) -> str:
        """
        Render a compiled template with the given variables.

        Args:
            template: Compiled Jinja2 template
            variables: Variables to use in template rendering

        Returns:
            Rendered template string

        Raises:
            TemplateError: If template rendering fails
        """
        try:
            result: str = template.render(**variables)
            return result
        except TemplateError as e:
            raise TemplateError(f"Template rendering failed: {e}") from e

    def render_string(self, template_str: str, variables: Dict[str, Any]) -> str:
        """
        Compile and render a template string in one step.

        Args:
            template_str: The template string to compile and render
            variables: Variables to use in template rendering

        Returns:
            Rendered template string
        """
        template = self.compile_template(template_str)
        return self.render_template(template, variables)
