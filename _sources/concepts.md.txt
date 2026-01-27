# Core Concepts

PromptKit is built around **structured prompt engineering** - treating prompts as first-class artifacts with schemas, validation, and reusability.

## Key Components

### Prompts

A Prompt contains:
- **Template**: Jinja2 template with variables
- **Schema**: Type definitions for input validation  
- **Metadata**: Name and description

```python
from promptkit import Prompt, load_prompt

# Load from YAML
prompt = load_prompt("greeting.yaml")

# Or create programmatically
prompt = Prompt(
    name="greeting",
    description="Personal greeting",
    template="Hello {{ name }}!",
    input_schema={"name": "str"}
)
```

### Engines

Engines provide a unified interface to LLM providers:

```python
from promptkit import OpenAIEngine
from promptkit.engines import OllamaEngine

# Cloud
engine = OpenAIEngine(api_key="sk-...", model="gpt-4o-mini")

# Local  
engine = OllamaEngine(model="llama2")
```

### Runner

The runner orchestrates prompt execution:

```python
from promptkit import run_prompt

response = run_prompt(prompt, {"name": "Alice"}, engine)
```

## Workflow

### Basic Execution

```python
from promptkit import load_prompt, run_prompt, OpenAIEngine

prompt = load_prompt("greeting.yaml")
engine = OpenAIEngine(api_key="sk-...")
response = run_prompt(prompt, {"name": "Alice"}, engine)
```

### Template Preview

```python
prompt = load_prompt("greeting.yaml")
rendered = prompt.render({"name": "Alice"})
print(rendered)
```

### Validation

Inputs are validated against schemas before rendering:

```yaml
input_schema:
  name: str           # Required string
  age: int            # Required integer
  email: "str | None" # Optional string
```

## YAML Format

```yaml
name: my_prompt
description: What this prompt does
template: |
  Hello {{ name }}!
  {% if context %}
  Context: {{ context }}
  {% endif %}
input_schema:
  name: str
  context: "str | None"
```
