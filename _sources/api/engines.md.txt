# Engines API Reference

## Base Engine

### BaseEngine

Abstract base class for all engines.

```python
from promptkit.engines.base import BaseEngine

class BaseEngine(ABC):
    def __init__(self, model: str = "default"):
        self.model = model

    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

    async def generate_async(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_info(self) -> dict[str, Any]:
        return {"engine": self.__class__.__name__, "model": self.model}

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Optional[float]:
        return None
```

### EngineError

Exception for engine errors.

```python
from promptkit.engines.base import EngineError

raise EngineError("API request failed")
```

## OpenAI Engine

### OpenAIEngine

```python
from promptkit import OpenAIEngine

engine = OpenAIEngine(
    api_key="sk-...",
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=1000,
    base_url="https://api.openai.com/v1"
)
```

#### Parameters

- `api_key`: OpenAI API key
- `model`: Model name (default: "gpt-4o-mini")
- `temperature`: Sampling temperature 0.0-2.0 (default: 0.7)
- `max_tokens`: Max tokens to generate (optional)
- `base_url`: API base URL (for compatible APIs)

#### Methods

**`generate(prompt: str) -> str`**

Generate a response synchronously.

**`generate_async(prompt: str) -> str`**

Generate a response asynchronously.

**`estimate_cost(input_tokens: int, output_tokens: int) -> Optional[float]`**

Estimate cost in USD.

```python
cost = engine.estimate_cost(1000, 500)
```

## Ollama Engine

### OllamaEngine

```python
from promptkit.engines import OllamaEngine

engine = OllamaEngine(
    model="llama2",
    base_url="http://localhost:11434",
    temperature=0.7,
    max_tokens=1000
)
```

#### Parameters

- `model`: Ollama model name (default: "llama2")
- `base_url`: Ollama API URL (default: "http://localhost:11434")
- `temperature`: Sampling temperature 0.0-1.0 (default: 0.7)
- `max_tokens`: Max tokens to generate (optional)

#### Methods

Same as OpenAIEngine.

## Creating Custom Engines

```python
from promptkit.engines.base import BaseEngine, EngineError

class MyEngine(BaseEngine):
    def __init__(self, api_key: str, model: str = "default"):
        super().__init__(model)
        self.api_key = api_key

    def generate(self, prompt: str) -> str:
        # Implement API call
        return "response"
```
