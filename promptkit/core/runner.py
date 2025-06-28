"""
Prompt execution orchestrator.

This module provides the main runner functionality that orchestrates
prompt rendering and LLM execution with proper error handling.
"""

from typing import Any, Dict

from promptkit.core.prompt import Prompt
from promptkit.engines.base import BaseEngine
from promptkit.utils.logging import get_logger

logger = get_logger(__name__)


def run_prompt(
    prompt: Prompt,
    inputs: Dict[str, Any],
    engine: BaseEngine,
    validate_inputs: bool = True,
) -> str:
    """
    Execute a prompt with the given inputs using the specified engine.

    This is the main orchestration function that:
    1. Validates inputs against the prompt schema
    2. Renders the prompt template
    3. Sends the rendered prompt to the LLM engine
    4. Returns the response

    Args:
        prompt: The prompt to execute
        inputs: Input variables for the prompt template
        engine: The LLM engine to use for generation
        validate_inputs: Whether to validate inputs against schema

    Returns:
        The LLM's response text

    Raises:
        ValidationError: If input validation fails
        TemplateError: If template rendering fails
        EngineError: If LLM generation fails

    Example:
        >>> from promptkit.core.loader import load_prompt
        >>> from promptkit.engines.openai import OpenAIEngine
        >>>
        >>> prompt = load_prompt("greet_user.yaml")
        >>> engine = OpenAIEngine(api_key="sk-...")
        >>> response = run_prompt(prompt, {"name": "Alice"}, engine)
    """
    logger.info(
        f"Running prompt '{prompt.name}' with engine {engine.__class__.__name__}"
    )

    try:
        rendered_prompt = prompt.render(inputs, validate=validate_inputs)
        logger.debug(f"Rendered prompt: {rendered_prompt[:100]}...")

        response = engine.generate(rendered_prompt)
        logger.info(f"Generated response of length {len(response)}")

        return response

    except Exception as e:
        logger.error(f"Failed to run prompt '{prompt.name}': {e}")
        raise


async def run_prompt_async(
    prompt: Prompt,
    inputs: Dict[str, Any],
    engine: BaseEngine,
    validate_inputs: bool = True,
) -> str:
    """
    Asynchronously execute a prompt with the given inputs using the specified engine.

    Args:
        prompt: The prompt to execute
        inputs: Input variables for the prompt template
        engine: The LLM engine to use for generation
        validate_inputs: Whether to validate inputs against schema

    Returns:
        The LLM's response text

    Raises:
        ValidationError: If input validation fails
        TemplateError: If template rendering fails
        EngineError: If LLM generation fails
    """
    logger.info(
        f"Running prompt '{prompt.name}' async with engine {engine.__class__.__name__}"
    )

    try:
        rendered_prompt = prompt.render(inputs, validate=validate_inputs)
        logger.debug(f"Rendered prompt: {rendered_prompt[:100]}...")

        if hasattr(engine, "generate_async"):
            response = await engine.generate_async(rendered_prompt)
        else:
            response = engine.generate(rendered_prompt)

        logger.info(f"Generated response of length {len(response)}")
        return response

    except Exception as e:
        logger.error(f"Failed to run prompt '{prompt.name}' async: {e}")
        raise
