"""
OpenAI engine implementation.

This module provides an engine implementation for OpenAI's GPT models
using the OpenAI API.
"""

import json
from typing import Any, Optional

import httpx

from promptkit.engines.base import BaseEngine, EngineError
from promptkit.utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIEngine(BaseEngine):
    """
    OpenAI engine implementation using the OpenAI API.

    Supports all OpenAI chat models including GPT-3.5, GPT-4, and newer variants.
    """

    # Model pricing per 1K tokens (input, output) in USD
    MODEL_PRICING = {
        "gpt-3.5-turbo": (0.0010, 0.0020),
        "gpt-3.5-turbo-1106": (0.0010, 0.0020),
        "gpt-4": (0.03, 0.06),
        "gpt-4-turbo": (0.01, 0.03),
        "gpt-4-turbo-preview": (0.01, 0.03),
        "gpt-4o": (0.005, 0.015),
        "gpt-4o-mini": (0.00015, 0.0006),
    }

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        """
        Initialize the OpenAI engine.

        Args:
            api_key: OpenAI API key
            model: OpenAI model name
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            base_url: API base URL (for compatible APIs)
        """
        super().__init__(model)
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url.rstrip("/")

        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    def generate(self, prompt: str) -> str:
        """
        Generate a response using OpenAI's chat completions API.

        Args:
            prompt: The prompt text to send to the model

        Returns:
            The generated response text

        Raises:
            EngineError: If the API request fails
        """
        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
            }

            if self.max_tokens:
                payload["max_tokens"] = self.max_tokens

            logger.debug(f"Sending request to OpenAI API with model {self.model}")

            response = self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )

            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_data = response.json()
                    error_detail = error_data.get("error", {}).get(
                        "message", error_detail
                    )
                except json.JSONDecodeError:
                    pass

                raise EngineError(
                    f"OpenAI API error (status {response.status_code}): {error_detail}"
                )

            data = response.json()

            if "choices" not in data or not data["choices"]:
                raise EngineError("No choices returned from OpenAI API")

            content: str = data["choices"][0]["message"]["content"]

            if content is None:
                raise EngineError("No content in OpenAI API response")

            logger.debug(f"Received response of length {len(content)}")
            return content

        except httpx.RequestError as e:
            raise EngineError(f"Request to OpenAI API failed: {e}") from e
        except KeyError as e:
            raise EngineError(
                f"Unexpected OpenAI API response format: missing {e}"
            ) from e
        except Exception as e:
            raise EngineError(f"Unexpected error calling OpenAI API: {e}") from e

    async def generate_async(self, prompt: str) -> str:
        """
        Asynchronously generate a response using OpenAI's API.

        Args:
            prompt: The prompt text to send to the model

        Returns:
            The generated response text

        Raises:
            EngineError: If the API request fails
        """
        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
            }

            if self.max_tokens:
                payload["max_tokens"] = self.max_tokens

            logger.debug(f"Sending async request to OpenAI API with model {self.model}")

            async with httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                )

            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_data = response.json()
                    error_detail = error_data.get("error", {}).get(
                        "message", error_detail
                    )
                except json.JSONDecodeError:
                    pass

                raise EngineError(
                    f"OpenAI API error (status {response.status_code}): {error_detail}"
                )

            data = response.json()
            content: str = data["choices"][0]["message"]["content"]

            if content is None:
                raise EngineError("No content in OpenAI API response")

            logger.debug(f"Received async response of length {len(content)}")
            return content

        except httpx.RequestError as e:
            raise EngineError(f"Async request to OpenAI API failed: {e}") from e
        except Exception as e:
            raise EngineError(f"Unexpected error in async OpenAI API call: {e}") from e

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Optional[float]:
        """
        Estimate the cost for the given token counts using OpenAI pricing.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD, or None if model pricing is unknown
        """
        if self.model not in self.MODEL_PRICING:
            return None

        input_price, output_price = self.MODEL_PRICING[self.model]

        input_cost = (input_tokens / 1000) * input_price
        output_cost = (output_tokens / 1000) * output_price

        return input_cost + output_cost

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current OpenAI model."""
        info = super().get_model_info()
        info.update(
            {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "base_url": self.base_url,
            }
        )
        return info

    def __del__(self) -> None:
        """Clean up the HTTP client when the engine is destroyed."""
        if hasattr(self, "_client"):
            self._client.close()
