"""
Ollama engine implementation for local LLM models.

This module provides an engine implementation for Ollama,
allowing the use of local LLM models.
"""

from typing import Any, Optional

import httpx

from promptkit.engines.base import BaseEngine, EngineError
from promptkit.utils.logging import get_logger

logger = get_logger(__name__)


class OllamaEngine(BaseEngine):
    """
    Ollama engine implementation for local LLM models.

    Ollama allows you to run large language models locally on your machine.
    This engine provides integration with Ollama's API.
    """

    def __init__(
        self,
        model: str = "llama2",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> None:
        """
        Initialize the Ollama engine.

        Args:
            model: Ollama model name (e.g., "llama2", "codellama", "mistral")
            base_url: Ollama API base URL
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
        """
        super().__init__(model)
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens

        self._client = httpx.Client(timeout=300.0)  # Longer timeout for local models

    def generate(self, prompt: str) -> str:
        """
        Generate a response using Ollama's API.

        Args:
            prompt: The prompt text to send to the model

        Returns:
            The generated response text

        Raises:
            EngineError: If the API request fails or Ollama is not available
        """
        try:
            payload: dict[str, Any] = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                },
            }

            if self.max_tokens:
                payload["options"]["num_predict"] = self.max_tokens

            logger.debug(f"Sending request to Ollama with model {self.model}")

            response = self._client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )

            if response.status_code != 200:
                if response.status_code == 404:
                    raise EngineError(
                        f"Model '{self.model}' not found. "
                        f"Please install it with: ollama pull {self.model}"
                    )

                raise EngineError(
                    f"Ollama API error (status {response.status_code}): {response.text}"
                )

            data = response.json()

            if "response" not in data:
                raise EngineError("No response field in Ollama API response")

            content: str = data["response"]
            logger.debug(f"Received response of length {len(content)}")

            return content

        except httpx.ConnectError:
            raise EngineError(
                "Cannot connect to Ollama. Please ensure Ollama is running locally. "
                "Install with: https://ollama.ai"
            )
        except httpx.RequestError as e:
            raise EngineError(f"Request to Ollama API failed: {e}") from e
        except Exception as e:
            raise EngineError(f"Unexpected error calling Ollama API: {e}") from e

    async def generate_async(self, prompt: str) -> str:
        """
        Asynchronously generate a response using Ollama's API.

        Args:
            prompt: The prompt text to send to the model

        Returns:
            The generated response text

        Raises:
            EngineError: If the API request fails
        """
        try:
            payload: dict[str, Any] = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                },
            }

            if self.max_tokens:
                payload["options"]["num_predict"] = self.max_tokens

            logger.debug(f"Sending async request to Ollama with model {self.model}")

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )

            if response.status_code != 200:
                if response.status_code == 404:
                    raise EngineError(
                        f"Model '{self.model}' not found. "
                        f"Please install it with: ollama pull {self.model}"
                    )

                raise EngineError(
                    f"Ollama API error (status {response.status_code}): {response.text}"
                )

            data = response.json()
            content: str = data["response"]

            logger.debug(f"Received async response of length {len(content)}")
            return content

        except httpx.ConnectError:
            raise EngineError(
                "Cannot connect to Ollama. Please ensure Ollama is running locally."
            )
        except httpx.RequestError as e:
            raise EngineError(f"Async request to Ollama API failed: {e}") from e
        except Exception as e:
            raise EngineError(f"Unexpected error in async Ollama API call: {e}") from e

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Optional[float]:
        """
        Estimate the cost for Ollama (which is free for local models).

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Always returns 0.0 since Ollama is free
        """
        return 0.0

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current Ollama model."""
        info = super().get_model_info()
        info.update(
            {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "base_url": self.base_url,
                "cost": "free",
            }
        )
        return info

    def list_available_models(self) -> list[str]:
        """
        List all available models in the local Ollama installation.

        Returns:
            List of available model names

        Raises:
            EngineError: If Ollama is not available
        """
        try:
            response = self._client.get(f"{self.base_url}/api/tags")

            if response.status_code != 200:
                raise EngineError(f"Failed to list models: {response.text}")

            data = response.json()
            return [model["name"] for model in data.get("models", [])]

        except httpx.ConnectError:
            raise EngineError(
                "Cannot connect to Ollama. Please ensure Ollama is running locally."
            )
        except Exception as e:
            raise EngineError(f"Failed to list Ollama models: {e}") from e

    def __del__(self) -> None:
        """Clean up the HTTP client when the engine is destroyed."""
        if hasattr(self, "_client"):
            self._client.close()
