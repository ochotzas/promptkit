# PromptKit

A production-grade library for structured prompt engineering for LLMs. Define, validate, and execute LLM prompts using YAML files with input validation, engine abstraction, and CLI support.

## Features

- 📝 **YAML-based prompt definitions** with Jinja2 templating
- 🔍 **Input validation** using Pydantic schemas
- 🏗️ **Engine abstraction** supporting OpenAI and local models
- 💰 **Token estimation** and cost calculation
- 🖥️ **CLI interface** for quick prompt execution
- 🧪 **Fully tested** with comprehensive test suite

## Installation

```bash
pip install promptkit-core
```

For development:

```bash
pip install promptkit-core[dev]
```

## 📚 Documentation

For detailed usage and examples, please refer to the [PromptKit Documentation](https://ochotzas.github.io/promptkit/).

## Repository

Source code: [https://github.com/ochotzas/promptkit](https://github.com/ochotzas/promptkit)

## Quick Start

### 1. Define a prompt in YAML

Create `greet_user.yaml`:

```yaml
name: greet_user
description: Basic greeting
template: |
  Hello {{ name }}, how can I help you today?
input_schema:
  name: str
```

### 2. Use in Python

```python
from promptkit.core.loader import load_prompt
from promptkit.core.runner import run_prompt
from promptkit.engines.openai import OpenAIEngine

# Load prompt from YAML
prompt = load_prompt("greet_user")

# Configure engine
engine = OpenAIEngine(api_key="sk-...")

# Run prompt
response = run_prompt(prompt, {"name": "Alice"}, engine)
print(response)
```

### 3. Use the CLI

```bash
# Run a prompt
promptkit run greet_user --key sk-... --name Alice

# Just render the template
promptkit render greet_user --name Alice

# Validate prompt structure
promptkit lint greet_user
```

## Prompt YAML Structure

```yaml
name: prompt_identifier
description: What this prompt does
template: |
  Your Jinja2 template here with {{ variables }}
input_schema:
  variable_name: str
  another_var: int
  optional_var: "str | None"
```

## Supported Engines

- **OpenAI**: Complete OpenAI API support
- **Ollama**: Local model support (work in progress)

## Token Estimation

```python
from promptkit.utils.tokens import estimate_tokens, estimate_cost

tokens = estimate_tokens("Your prompt text here")
cost = estimate_cost(tokens, "gpt-4")
print(f"Estimated cost: ${cost:.4f}")
```

## Development

```bash
# Clone the repository
git clone https://github.com/ochotzas/promptkit.git
cd promptkit

# Install development dependencies
pip install -e .[dev]

# Run tests
pytest

# Format code
black .
isort .

# Type checking
mypy promptkit/
```

## License

MIT License - see LICENSE file for details.
