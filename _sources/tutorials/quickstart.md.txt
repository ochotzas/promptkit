# Quick Start Guide

Get up and running with PromptKit in minutes! This guide will walk you through creating your first prompt and running it with different engines.

## Prerequisites

Make sure you have Python 3.10+ installed and PromptKit installed:

```bash
pip install promptkit-core
```

## Your First Prompt

Let's create a simple greeting prompt that demonstrates the core concepts of PromptKit.

### 1. Create a Prompt File

Create a file called `hello.yaml`:

```yaml
name: hello_world
description: A simple greeting prompt that personalizes messages
template: |
  Hello {{ name }}!

  {% if context %}
  I understand you're interested in {{ context }}.
  {% endif %}

  How can I help you today?

input_schema:
  name: str
  context: "str | None"
```

### 2. Use in Python

```python
from promptkit.core.loader import load_prompt
from promptkit.core.runner import run_prompt
from promptkit.engines.openai import OpenAIEngine

# Load the prompt
prompt = load_prompt("hello.yaml")

# Create an engine (you'll need an OpenAI API key)
engine = OpenAIEngine(api_key="your-api-key-here")

# Run the prompt
response = run_prompt(
    prompt,
    {"name": "Alice", "context": "machine learning"},
    engine
)

print(response)
```

### 3. Use the CLI

PromptKit comes with a powerful CLI for quick experimentation:

```bash
# Run the prompt interactively
promptkit run hello.yaml --name Alice --context "machine learning"

# Just render the template (no AI call)
promptkit render hello.yaml --name Alice --context "machine learning"

# Validate the prompt structure
promptkit lint hello.yaml

# Get detailed information about the prompt
promptkit info hello.yaml
```

## Key Concepts

### YAML Structure

Every PromptKit prompt has these key components:

- **`name`**: Unique identifier for your prompt
- **`description`**: Human-readable description
- **`template`**: Jinja2 template with variables
- **`input_schema`**: Pydantic-style type definitions

### Template Variables

Use Jinja2 syntax for dynamic content:

```yaml
template: |
  Hello {{ name }}!
  {% if urgent %}
  🚨 URGENT: {{ message }}
  {% else %}
  📝 Note: {{ message }}
  {% endif %}
```

### Input Validation

PromptKit validates inputs before rendering:

```yaml
input_schema:
  name: str                    # Required string
  age: int                     # Required integer
  email: "str | None"          # Optional string
  tags: "list[str]"            # List of strings
  metadata: "dict[str, Any]"   # Dictionary
```

## Next Steps

- 📖 [Create Your First Prompt](first-prompt.md) - Detailed walkthrough
- 🎨 [Advanced Templates](advanced-templates.md) - Complex Jinja2 patterns
- ✅ [Input Validation](validation.md) - Schema design best practices
- 🔧 [API Reference](../api/core.md) - Complete API documentation

## Common Patterns

### Environment Variables

Store API keys securely:

```bash
export OPENAI_API_KEY="your-key-here"
promptkit run hello.yaml --name Alice
```

### Multiple Engines

```python
from promptkit.engines.openai import OpenAIEngine
from promptkit.engines.ollama import OllamaEngine

# Use OpenAI
openai_engine = OpenAIEngine()

# Use local Ollama
ollama_engine = OllamaEngine(model="llama2")
```

### Batch Processing

```python
names = ["Alice", "Bob", "Charlie"]
responses = []

for name in names:
    response = run_prompt(prompt, {"name": name}, engine)
    responses.append(response)
```

You're now ready to build sophisticated prompt-driven applications with PromptKit!
