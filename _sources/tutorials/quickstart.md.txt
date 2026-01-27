# Quick Start

Get up and running with PromptKit in minutes.

## Prerequisites

- Python 3.10+
- PromptKit installed: `pip install promptkit-core`

## Create a Prompt

Create `hello.yaml`:

```yaml
name: hello
description: A simple greeting prompt
template: |
  Hello {{ name }}!
  
  {% if context %}
  I see you're interested in {{ context }}.
  {% endif %}
  
  How can I help?

input_schema:
  name: str
  context: "str | None"
```

## Use in Python

```python
from promptkit import load_prompt, run_prompt, OpenAIEngine

prompt = load_prompt("hello.yaml")

engine = OpenAIEngine(api_key="sk-...")

response = run_prompt(
    prompt,
    {"name": "Alice", "context": "machine learning"},
    engine
)
print(response)
```

## Use the CLI

```bash
# Run with AI
promptkit run hello.yaml --name Alice --context "machine learning"

# Render template only
promptkit render hello.yaml --name Alice

# Validate structure
promptkit lint hello.yaml

# Get info
promptkit info hello.yaml
```

## YAML Structure

- `name`: Unique identifier
- `description`: What the prompt does
- `template`: Jinja2 template
- `input_schema`: Input types

## Template Syntax

```yaml
template: |
  Hello {{ name }}!
  {% if urgent %}
  🚨 URGENT: {{ message }}
  {% else %}
  📝 Note: {{ message }}
  {% endif %}
```

## Input Types

```yaml
input_schema:
  name: str                # Required string
  age: int                 # Required integer
  email: "str | None"      # Optional string
```

## Next Steps

- [First Prompt Tutorial](first-prompt.md)
- [Input Validation](validation.md)
- [API Reference](../api/core.md)
