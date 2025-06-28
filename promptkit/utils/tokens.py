"""
Token estimation and cost calculation utilities.

This module provides functionality to estimate token usage and
calculate costs for different LLM models.
"""

import re
from typing import Dict, Optional

# Approximate token estimation based on character count
# This is a rough approximation; actual tokenization varies by model
CHARS_PER_TOKEN = 4


MODEL_PRICING: Dict[str, tuple[float, float]] = {
    # OpenAI Models
    "gpt-3.5-turbo": (0.0010, 0.0020),
    "gpt-3.5-turbo-1106": (0.0010, 0.0020),
    "gpt-4": (0.03, 0.06),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-4-turbo-preview": (0.01, 0.03),
    "gpt-4o": (0.005, 0.015),
    "gpt-4o-mini": (0.00015, 0.0006),
    # Anthropic Models (example pricing)
    "claude-3-opus": (0.015, 0.075),
    "claude-3-sonnet": (0.003, 0.015),
    "claude-3-haiku": (0.00025, 0.00125),
    # Local models (free)
    "ollama": (0.0, 0.0),
}


def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text string.

    This is a rough approximation based on character count and word boundaries.
    For precise token counts, use the specific tokenizer for your model.

    Args:
        text: The text to analyze

    Returns:
        Estimated number of tokens

    Example:
        >>> tokens = estimate_tokens("Hello, world!")
        >>> print(f"Estimated tokens: {tokens}")
    """
    if not text:
        return 0

    # Basic estimation: average 4 characters per token
    char_based = len(text) / CHARS_PER_TOKEN

    # Word-based estimation as a cross-check
    words = len(re.findall(r"\b\w+\b", text))
    word_based = words * 1.3  # Average 1.3 tokens per word

    # Use the higher estimate for safety
    return int(max(char_based, word_based))


def estimate_cost(
    input_tokens: int, output_tokens: int = 0, model: str = "gpt-4o-mini"
) -> Optional[float]:
    """
    Estimate the cost for the given token counts and model.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name for pricing lookup

    Returns:
        Estimated cost in USD, or None if model pricing is unknown

    Example:
        >>> cost = estimate_cost(1000, 500, "gpt-4o-mini")
        >>> print(f"Estimated cost: ${cost:.4f}")
    """
    if model not in MODEL_PRICING:
        return None

    input_price, output_price = MODEL_PRICING[model]

    input_cost = (input_tokens / 1000) * input_price
    output_cost = (output_tokens / 1000) * output_price

    return input_cost + output_cost


def estimate_prompt_cost(
    prompt_text: str, model: str = "gpt-4o-mini"
) -> Optional[float]:
    """
    Estimate the cost for a prompt text (input only).

    Args:
        prompt_text: The prompt text to analyze
        model: Model name for pricing lookup

    Returns:
        Estimated input cost in USD, or None if model pricing is unknown
    """
    tokens = estimate_tokens(prompt_text)
    return estimate_cost(tokens, 0, model)


def get_model_pricing(model: str) -> Optional[tuple[float, float]]:
    """
    Get the pricing information for a specific model.

    Args:
        model: Model name

    Returns:
        Tuple of (input_price_per_1k, output_price_per_1k) or None if unknown
    """
    return MODEL_PRICING.get(model)


def list_supported_models() -> list[str]:
    """
    Get a list of all models with known pricing.

    Returns:
        List of supported model names
    """
    return list(MODEL_PRICING.keys())


def format_cost(cost: float) -> str:
    """
    Format a cost value for display.

    Args:
        cost: Cost in USD

    Returns:
        Formatted cost string

    Example:
        >>> formatted = format_cost(0.001234)
        >>> print(formatted)  # "$0.0012"
    """
    if cost >= 0.01:
        return f"${cost:.4f}"
    elif cost >= 0.001:
        return f"${cost:.4f}"
    else:
        return f"${cost:.6f}"
