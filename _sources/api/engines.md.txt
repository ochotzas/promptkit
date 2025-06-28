# Engines API Reference

Complete reference for PromptKit's engine system and built-in engines.

## Base Engine

### BaseEngine Class

Abstract base class that all engines must inherit from.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Iterator

class BaseEngine(ABC):
    """
    Abstract base class for all PromptKit engines.

    Engines are responsible for executing prompts against specific
    language models or services.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the engine.

        Args:
            config: Engine-specific configuration
        """
        self.config = config or {}

    @abstractmethod
    def generate(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """
        Generate response for the given prompt.

        Args:
            prompt: The prompt text to process
            **kwargs: Engine-specific parameters

        Returns:
            Generated response text

        Raises:
            EngineError: If generation fails
        """

    @abstractmethod
    async def generate_async(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """
        Asynchronously generate response for the given prompt.

        Args:
            prompt: The prompt text to process
            **kwargs: Engine-specific parameters

        Returns:
            Generated response text

        Raises:
            EngineError: If generation fails
        """

    def generate_stream(
        self,
        prompt: str,
        **kwargs
    ) -> Iterator[str]:
        """
        Generate streaming response for the given prompt.

        Args:
            prompt: The prompt text to process
            **kwargs: Engine-specific parameters

        Yields:
            Response chunks as they're generated

        Raises:
            EngineError: If generation fails
        """
        # Default implementation - subclasses can override
        response = self.generate(prompt, **kwargs)
        yield response

    def estimate_cost(self, prompt: str, **kwargs) -> float:
        """
        Estimate cost for processing the prompt.

        Args:
            prompt: The prompt text
            **kwargs: Engine-specific parameters

        Returns:
            Estimated cost in USD
        """
        return 0.0  # Default implementation

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model information
        """
        return {
            "name": "unknown",
            "version": "unknown",
            "max_tokens": None,
            "supports_streaming": False
        }

    def validate_config(self) -> bool:
        """
        Validate engine configuration.

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        return True
```

## OpenAI Engine

### OpenAIEngine Class

```python
from promptkit.engines.base import BaseEngine
from typing import Dict, Any, Optional, Iterator, List

class OpenAIEngine(BaseEngine):
    """
    Engine for OpenAI GPT models.

    Supports GPT-3.5, GPT-4, and other OpenAI models with
    both completion and chat completion APIs.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        **kwargs
    ):
        """
        Initialize OpenAI engine.

        Args:
            api_key: OpenAI API key
            model: Model name (e.g., 'gpt-3.5-turbo', 'gpt-4')
            base_url: Custom API base URL
            organization: OpenAI organization ID
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            **kwargs: Additional OpenAI client parameters
        """
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.organization = organization
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize OpenAI client
        self._client = self._create_client(**kwargs)

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Generate response using OpenAI API.

        Args:
            prompt: Input prompt text
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty (-2.0 to 2.0)
            presence_penalty: Presence penalty (-2.0 to 2.0)
            stop: Stop sequences
            **kwargs: Additional model parameters

        Returns:
            Generated response text

        Raises:
            EngineError: If API call fails
        """

    async def generate_async(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """
        Asynchronously generate response using OpenAI API.

        Args:
            prompt: Input prompt text
            **kwargs: Model parameters (same as generate())

        Returns:
            Generated response text
        """

    def generate_stream(
        self,
        prompt: str,
        **kwargs
    ) -> Iterator[str]:
        """
        Generate streaming response using OpenAI API.

        Args:
            prompt: Input prompt text
            **kwargs: Model parameters (same as generate())

        Yields:
            Response chunks as they're generated
        """

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Generate response using chat completion API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Model parameters (same as generate())

        Returns:
            Generated response text
        """

    def estimate_cost(self, prompt: str, **kwargs) -> float:
        """
        Estimate cost for the prompt.

        Args:
            prompt: Input prompt text
            **kwargs: Model parameters

        Returns:
            Estimated cost in USD
        """

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get OpenAI model information.

        Returns:
            Dictionary with model details
        """
        return {
            "name": self.model,
            "provider": "openai",
            "max_tokens": self._get_max_tokens(),
            "supports_streaming": True,
            "supports_chat": True,
            "cost_per_1k_tokens": self._get_cost_info()
        }

    def validate_config(self) -> bool:
        """
        Validate OpenAI configuration.

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationError: If API key is missing or invalid
        """
```

## Azure OpenAI Engine

### AzureOpenAIEngine Class

```python
class AzureOpenAIEngine(BaseEngine):
    """
    Engine for Azure OpenAI Service.

    Supports Azure-hosted OpenAI models with custom endpoints
    and authentication.
    """

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment_name: str,
        api_version: str = "2023-05-15",
        timeout: float = 30.0,
        **kwargs
    ):
        """
        Initialize Azure OpenAI engine.

        Args:
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
            deployment_name: Deployment name in Azure
            api_version: API version to use
            timeout: Request timeout in seconds
            **kwargs: Additional parameters
        """
        super().__init__()
        self.api_key = api_key
        self.endpoint = endpoint
        self.deployment_name = deployment_name
        self.api_version = api_version
        self.timeout = timeout

        self._client = self._create_azure_client(**kwargs)

    # Similar methods to OpenAIEngine but using Azure endpoints
```

## Anthropic Engine

### AnthropicEngine Class

```python
class AnthropicEngine(BaseEngine):
    """
    Engine for Anthropic Claude models.

    Supports Claude-1, Claude-2, and Claude-Instant models.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-2",
        timeout: float = 30.0,
        max_retries: int = 3,
        **kwargs
    ):
        """
        Initialize Anthropic engine.

        Args:
            api_key: Anthropic API key
            model: Model name (e.g., 'claude-2', 'claude-instant-1')
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            **kwargs: Additional parameters
        """
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

        self._client = self._create_client(**kwargs)

    def generate(
        self,
        prompt: str,
        max_tokens_to_sample: int = 1000,
        temperature: float = 0.7,
        top_p: float = 1.0,
        top_k: int = -1,
        stop_sequences: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Generate response using Anthropic API.

        Args:
            prompt: Input prompt text
            max_tokens_to_sample: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            stop_sequences: Stop sequences
            **kwargs: Additional model parameters

        Returns:
            Generated response text
        """
```

## Local Engine

### LocalEngine Class

```python
class LocalEngine(BaseEngine):
    """
    Engine for local/self-hosted models.

    Supports models running locally via APIs like Ollama,
    LocalAI, or custom endpoints.
    """

    def __init__(
        self,
        endpoint: str,
        model: str,
        api_format: str = "openai",  # "openai", "ollama", "custom"
        auth_token: Optional[str] = None,
        timeout: float = 60.0,
        **kwargs
    ):
        """
        Initialize local engine.

        Args:
            endpoint: Local model endpoint URL
            model: Model name
            api_format: API format to use
            auth_token: Authentication token if required
            timeout: Request timeout in seconds
            **kwargs: Additional parameters
        """
        super().__init__()
        self.endpoint = endpoint
        self.model = model
        self.api_format = api_format
        self.auth_token = auth_token
        self.timeout = timeout

        self._client = self._create_client(**kwargs)

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate response using local model API.

        Args:
            prompt: Input prompt text
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model parameters

        Returns:
            Generated response text
        """
```

## HuggingFace Engine

### HuggingFaceEngine Class

```python
class HuggingFaceEngine(BaseEngine):
    """
    Engine for HuggingFace models.

    Supports both Inference API and local transformers models.
    """

    def __init__(
        self,
        model: str,
        api_token: Optional[str] = None,
        use_local: bool = False,
        device: str = "auto",
        **kwargs
    ):
        """
        Initialize HuggingFace engine.

        Args:
            model: HuggingFace model name
            api_token: HuggingFace API token
            use_local: Whether to load model locally
            device: Device to use for local models
            **kwargs: Additional parameters
        """
        super().__init__()
        self.model = model
        self.api_token = api_token
        self.use_local = use_local
        self.device = device

        if use_local:
            self._load_local_model(**kwargs)
        else:
            self._setup_api_client(**kwargs)

    def generate(
        self,
        prompt: str,
        max_length: int = 1000,
        temperature: float = 0.7,
        do_sample: bool = True,
        **kwargs
    ) -> str:
        """
        Generate response using HuggingFace model.

        Args:
            prompt: Input prompt text
            max_length: Maximum sequence length
            temperature: Sampling temperature
            do_sample: Whether to use sampling
            **kwargs: Additional generation parameters

        Returns:
            Generated response text
        """
```

## Mock Engine

### MockEngine Class

```python
class MockEngine(BaseEngine):
    """
    Mock engine for testing purposes.

    Returns predefined responses or generates simple mock responses.
    """

    def __init__(
        self,
        responses: Optional[List[str]] = None,
        delay: float = 0.0,
        **kwargs
    ):
        """
        Initialize mock engine.

        Args:
            responses: List of predefined responses
            delay: Artificial delay to simulate API calls
            **kwargs: Additional parameters
        """
        super().__init__()
        self.responses = responses or ["Mock response"]
        self.delay = delay
        self.call_count = 0

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate mock response.

        Args:
            prompt: Input prompt (logged but not used)
            **kwargs: Ignored parameters

        Returns:
            Mock response
        """
        if self.delay > 0:
            import time
            time.sleep(self.delay)

        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response

    def set_response(self, response: str) -> None:
        """
        Set a single response for the next call.

        Args:
            response: Response to return
        """
        self.responses = [response]
        self.call_count = 0

    def set_responses(self, responses: List[str]) -> None:
        """
        Set multiple responses to cycle through.

        Args:
            responses: List of responses
        """
        self.responses = responses
        self.call_count = 0
```

## Engine Factory

### EngineFactory Class

```python
class EngineFactory:
    """
    Factory for creating engine instances.
    """

    @staticmethod
    def create_engine(
        engine_type: str,
        config: Dict[str, Any]
    ) -> BaseEngine:
        """
        Create an engine instance.

        Args:
            engine_type: Type of engine ('openai', 'anthropic', etc.)
            config: Engine configuration

        Returns:
            Engine instance

        Raises:
            ValueError: If engine type is not supported
        """
        engines = {
            'openai': OpenAIEngine,
            'azure_openai': AzureOpenAIEngine,
            'anthropic': AnthropicEngine,
            'local': LocalEngine,
            'huggingface': HuggingFaceEngine,
            'mock': MockEngine
        }

        if engine_type not in engines:
            raise ValueError(f"Unsupported engine type: {engine_type}")

        return engines[engine_type](**config)

    @staticmethod
    def list_engines() -> List[str]:
        """
        List available engine types.

        Returns:
            List of engine type names
        """
        return ['openai', 'azure_openai', 'anthropic', 'local', 'huggingface', 'mock']

def create_engine(engine_type: str, **config) -> BaseEngine:
    """
    Convenience function to create an engine.

    Args:
        engine_type: Type of engine
        **config: Engine configuration as keyword arguments

    Returns:
        Engine instance
    """
    return EngineFactory.create_engine(engine_type, config)
```

## Engine Configuration

### Configuration Examples

```python
# OpenAI Configuration
openai_config = {
    "api_key": "sk-...",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 1000
}

# Azure OpenAI Configuration
azure_config = {
    "api_key": "your-azure-key",
    "endpoint": "https://your-resource.openai.azure.com/",
    "deployment_name": "your-deployment",
    "api_version": "2023-05-15"
}

# Anthropic Configuration
anthropic_config = {
    "api_key": "your-anthropic-key",
    "model": "claude-2",
    "max_tokens_to_sample": 1000
}

# Local Model Configuration
local_config = {
    "endpoint": "http://localhost:11434",
    "model": "llama2",
    "api_format": "ollama"
}

# Create engines
from promptkit.engines import create_engine

openai_engine = create_engine("openai", **openai_config)
azure_engine = create_engine("azure_openai", **azure_config)
claude_engine = create_engine("anthropic", **anthropic_config)
local_engine = create_engine("local", **local_config)
```

## Engine Utilities

### Utility Functions

```python
def compare_engines(
    engines: List[BaseEngine],
    prompt: str,
    input_data: Dict[str, Any]
) -> Dict[str, str]:
    """
    Compare responses from multiple engines.

    Args:
        engines: List of engines to compare
        prompt: Prompt to test
        input_data: Input data for the prompt

    Returns:
        Dictionary mapping engine names to responses
    """

def benchmark_engine(
    engine: BaseEngine,
    prompts: List[str],
    iterations: int = 10
) -> Dict[str, float]:
    """
    Benchmark engine performance.

    Args:
        engine: Engine to benchmark
        prompts: List of test prompts
        iterations: Number of iterations per prompt

    Returns:
        Performance metrics
    """

def estimate_batch_cost(
    engine: BaseEngine,
    prompts: List[str]
) -> float:
    """
    Estimate cost for batch processing.

    Args:
        engine: Engine to use
        prompts: List of prompts to process

    Returns:
        Estimated total cost
    """
```

This reference covers all the engines and engine-related functionality in PromptKit. Each engine provides the same interface while supporting provider-specific features and optimizations.
