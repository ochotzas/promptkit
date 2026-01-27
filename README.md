<br/>
<p align="center">
  <h1 align="center">⚙️ PromptKit</h1>
</p>

<p align="center" style="font-size:1.15em;">
  A production-grade library for structured LLM prompt engineering.
  <br/>
  <br/>
  <img src="https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExNnA2ZzlxYnIzaW53dDUyZnVlY3JkcG5qNnpsZHlvbmhnYmdpaHQ0bSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3oKIPnAiaMCws8nOsE/giphy.gif" alt="Cat Typing on Computer" width="100" style="border-radius:7px;box-shadow:0 1px 4px #0001;opacity:0.85;margin-bottom:-6px;margin-top:6px;" />
  <br/>
  <a href="https://ochotzas.github.io/promptkit/" style="margin-top:2px;"><strong>Explore the docs »</strong></a>
  <br/>
  <br/>
  <a href="https://github.com/ochotzas/promptkit/issues">Report Bug</a>
  ·
  <a href="https://github.com/ochotzas/promptkit/issues">Request Feature</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/promptkit-core/"> <img alt="PyPI" src="https://img.shields.io/pypi/v/promptkit-core.svg?style=flat-square"></a>
  <a href="https://img.shields.io/badge/python-%3E%3D3.10-blue"><img alt="PyPI - Python Version" src="https://img.shields.io/badge/python-%3E%3D3.10-blue?style=flat-square"></a>
  <a href="https://github.com/ochotzas/promptkit/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/ochotzas/promptkit/ci.yml?branch=main&style=flat-square&label=tests"></a>
  <a href="https://github.com/ochotzas/promptkit/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/ochotzas/promptkit.svg?style=flat-square"></a>
</p>

-----

## Why PromptKit?

Managing prompts for Large Language Models can quickly become messy. Hardcoding prompts as f-strings mixes logic with presentation, lacks validation, and makes reuse difficult.

**PromptKit** solves this by treating your prompts as structured, version-controlled assets. By defining prompts in YAML files, you get:

- **Clean Separation**: Prompt templates are separate from application code
- **Safety & Reliability**: Built-in validation ensures prompts receive correct inputs
- **Reusability**: Define a prompt once, use it anywhere
- **Clarity**: Human-readable format anyone can understand

## Features

- 📝 **Declarative**: Define prompts in YAML with Jinja2 templating
- 🔍 **Validation**: Pydantic-based input validation before rendering
- 🏗️ **Engine Abstraction**: Supports OpenAI and Ollama
- 💰 **Cost Estimation**: Estimate token counts and costs before execution
- 🖥️ **CLI**: Render, run, lint, and inspect prompts from terminal
- 🧪 **Typed**: Full type hints for IDE support

## Quick Start

### Installation

```bash
pip install promptkit-core
```

### Define a Prompt

Create `greet.yaml`:

```yaml
name: greet
description: Generates a personalized greeting
template: |
  Hello {{ name }}!
  
  {% if context %}
  Context: {{ context }}
  {% endif %}
  
  How can I help you today?

input_schema:
  name: str
  context: "str | None"
```

### Use in Python

```python
from promptkit import load_prompt, run_prompt, OpenAIEngine

prompt = load_prompt("greet.yaml")

engine = OpenAIEngine(api_key="sk-...")

response = run_prompt(prompt, {"name": "Alice"}, engine)
print(response)
```

### Use the CLI

```bash
export OPENAI_API_KEY="sk-..."

# Run the prompt
promptkit run greet.yaml --name Alice

# Render template without calling AI
promptkit render greet.yaml --name Alice

# Validate prompt structure
promptkit lint greet.yaml

# Get prompt information
promptkit info greet.yaml

# Estimate costs
promptkit cost greet.yaml --model gpt-4 --name Alice
```

## Prompt Structure

Every prompt YAML file contains:

- `name`: Unique identifier
- `description`: Human-readable description
- `template`: Jinja2 template with variables
- `input_schema`: Type definitions for inputs

### Input Schema Types

```yaml
input_schema:
  name: str              # Required string
  age: int               # Required integer
  score: float           # Required float
  active: bool           # Required boolean
  tags: list             # Required list
  data: dict             # Required dictionary
  email: "str | None"    # Optional string
```

## Engines

### OpenAI

```python
from promptkit import OpenAIEngine

engine = OpenAIEngine(
    api_key="sk-...",
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=1000
)
```

### Ollama (Local)

```python
from promptkit.engines import OllamaEngine

engine = OllamaEngine(
    model="llama2",
    temperature=0.7
)
```

## Documentation

See the [documentation](https://ochotzas.github.io/promptkit/) for detailed guides and API reference.

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
