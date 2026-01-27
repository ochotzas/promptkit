# Advanced Examples

## Multi-Step Workflow

```python
from promptkit import load_prompt, run_prompt, OpenAIEngine

engine = OpenAIEngine(api_key="sk-...")

# Step 1: Analyze
analyze_prompt = load_prompt("analyze.yaml")
analysis = run_prompt(analyze_prompt, {"data": data}, engine)

# Step 2: Generate based on analysis
generate_prompt = load_prompt("generate.yaml")
result = run_prompt(generate_prompt, {"analysis": analysis}, engine)
```

## Dynamic Templates

```yaml
name: content
description: Generate content for different platforms
template: |
  {% set configs = {
    "blog": {"tone": "informative", "length": "long"},
    "twitter": {"tone": "casual", "length": "short"},
    "email": {"tone": "professional", "length": "medium"}
  } %}
  {% set config = configs[platform] %}
  
  Generate {{ config.length }} {{ config.tone }} content about {{ topic }}.

input_schema:
  platform: str
  topic: str
```

## Batch Processing

```python
from promptkit import load_prompt, run_prompt, OpenAIEngine

prompt = load_prompt("summarize.yaml")
engine = OpenAIEngine(api_key="sk-...")

documents = ["doc1...", "doc2...", "doc3..."]
summaries = []

for doc in documents:
    summary = run_prompt(prompt, {"document": doc}, engine)
    summaries.append(summary)
```

## Async Execution

```python
import asyncio
from promptkit import load_prompt
from promptkit.core.runner import run_prompt_async
from promptkit import OpenAIEngine

async def process_batch(documents):
    prompt = load_prompt("summarize.yaml")
    engine = OpenAIEngine(api_key="sk-...")
    
    tasks = [
        run_prompt_async(prompt, {"document": doc}, engine)
        for doc in documents
    ]
    return await asyncio.gather(*tasks)

summaries = asyncio.run(process_batch(documents))
```

## Error Handling

```python
from promptkit import load_prompt, run_prompt, OpenAIEngine
from promptkit.engines.base import EngineError
from pydantic import ValidationError

prompt = load_prompt("task.yaml")
engine = OpenAIEngine(api_key="sk-...")

try:
    result = run_prompt(prompt, inputs, engine)
except ValidationError as e:
    print(f"Invalid inputs: {e}")
except EngineError as e:
    print(f"LLM error: {e}")
```

## Local Development with Ollama

```python
from promptkit import load_prompt, run_prompt
from promptkit.engines import OllamaEngine

prompt = load_prompt("task.yaml")
engine = OllamaEngine(model="llama2")

result = run_prompt(prompt, {"query": "Hello"}, engine)
```
