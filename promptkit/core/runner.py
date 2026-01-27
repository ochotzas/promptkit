"""Prompt execution runner."""

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
    """Execute a prompt with the given inputs using the specified engine."""
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
    """Asynchronously execute a prompt."""
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
