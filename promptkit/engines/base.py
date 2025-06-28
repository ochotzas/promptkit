"""
Abstract base engine for LLM implementations.

This module defines the interface that all LLM engines must implement,
ensuring consistency across different providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class EngineError(Exception):
    """Base exception for engine-related errors."""

    pass


class BaseEngine(ABC):
    """
    Abstract base class for all LLM engines.

    All engine implementations must inherit from this class and implement
    the generate method. This ensures a consistent interface across
    different LLM providers.
    """

    def __init__(self, model: str = "default") -> None:
        """
        Initialize the engine.

        Args:
            model: The model name/identifier to use
        """
        self.model = model

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate a response for the given prompt.

        Args:
            prompt: The prompt text to send to the LLM

        Returns:
            The generated response text

        Raises:
            EngineError: If generation fails
        """
        pass

    async def generate_async(self, prompt: str) -> str:
        """
        Asynchronously generate a response for the given prompt.

        Default implementation falls back to synchronous generation.
        Engines that support async should override this method.

        Args:
            prompt: The prompt text to send to the LLM

        Returns:
            The generated response text

        Raises:
            EngineError: If generation fails
        """
        return self.generate(prompt)

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary containing model information
        """
        return {
            "engine": self.__class__.__name__,
            "model": self.model,
        }

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Optional[float]:
        """
        Estimate the cost for the given token counts.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD, or None if cost estimation is not supported
        """
        return None
