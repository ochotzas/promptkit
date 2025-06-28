# Core Concepts

This guide explains the fundamental concepts and architecture of PromptKit, helping you understand how to build robust prompt-driven applications.

## Overview

PromptKit is built around the idea of **structured prompt engineering** - treating prompts as first-class artifacts with clear schemas, validation, and reusability. Instead of hardcoding prompts in your application, you define them in YAML files with proper structure and type safety.

## Key Components

### 1. Prompts

A **Prompt** is the core abstraction in PromptKit. It consists of:

- **Template**: Jinja2 template with dynamic variables
- **Schema**: Type definitions for input validation
- **Metadata**: Name, description, and other properties

```python
from promptkit.core.prompt import Prompt

# Prompts are typically loaded from YAML files
prompt = load_prompt("my_prompt.yaml")

# But can also be created programmatically
prompt = Prompt(
    name="greeting",
    description="Personal greeting",
    template="Hello {{ name }}!",
    input_schema={"name": "str"}
)
```

### 2. Engines

**Engines** provide a unified interface to different LLM providers:

```python
from promptkit.engines.openai import OpenAIEngine
from promptkit.engines.ollama import OllamaEngine

# Cloud-based
openai_engine = OpenAIEngine(api_key="sk-...", model="gpt-4")

# Local
ollama_engine = OllamaEngine(model="llama2")
```

All engines implement the same interface, making it easy to switch between providers.

### 3. Runners

**Runners** execute prompts with engines and handle the complete lifecycle:

```python
from promptkit.core.runner import run_prompt

response = run_prompt(
    prompt=my_prompt,
    variables={"name": "Alice"},
    engine=my_engine
)
```

### 4. Loaders

**Loaders** handle reading prompts from various sources:

```python
from promptkit.core.loader import load_prompt

# Load from file (extension optional)
prompt = load_prompt("greeting.yaml")
prompt = load_prompt("greeting")  # Same as above

# Load from string
yaml_content = """
name: test
template: Hello {{ name }}
input_schema:
  name: str
"""
prompt = load_prompt_from_string(yaml_content)
```

## Architecture Patterns

### Separation of Concerns

PromptKit enforces clear separation between:

1. **Prompt Definition** (YAML files)
2. **Application Logic** (Python code)
3. **Engine Configuration** (runtime settings)

```
Application Code    ←→    Prompt Files    ←→    LLM Engines
     (Logic)              (Templates)           (Execution)
```

### Template-First Design

Templates are the primary interface. Your application logic doesn't need to know about specific LLM APIs or prompt formatting - it just provides data to templates.

```python
# Application provides data
user_data = {
    "name": "Alice",
    "preferences": ["coffee", "books"],
    "context": "birthday planning"
}

# Template handles formatting
template = """
Create a personalized message for {{ name }}.
Interests: {{ preferences | join(", ") }}
Context: {{ context }}
"""
```

### Type Safety

All inputs are validated against schemas before template rendering:

```yaml
input_schema:
  user_id: str                    # Required string
  age: int                        # Required integer
  preferences: "list[str] | None" # Optional list of strings
  metadata: "dict[str, Any]"      # Dictionary with any values
```

## Workflow Patterns

### 1. Simple Execution

```python
# Load → Validate → Render → Execute
prompt = load_prompt("my_prompt.yaml")
response = run_prompt(prompt, variables, engine)
```

### 2. Template Preview

```python
# Load → Validate → Render (no execution)
prompt = load_prompt("my_prompt.yaml")
rendered = prompt.render(variables)
print(rendered)  # See final prompt before sending to LLM
```

### 3. Batch Processing

```python
prompt = load_prompt("summarize.yaml")
summaries = []

for document in documents:
    variables = {"content": document.text, "style": "brief"}
    summary = run_prompt(prompt, variables, engine)
    summaries.append(summary)
```

### 4. Pipeline Composition

```python
# Multi-step workflows
extract_prompt = load_prompt("extract_data.yaml")
analyze_prompt = load_prompt("analyze_data.yaml")
summarize_prompt = load_prompt("summarize_analysis.yaml")

# Step 1: Extract
extracted = run_prompt(extract_prompt, {"text": raw_text}, engine)

# Step 2: Analyze
analysis = run_prompt(analyze_prompt, {"data": extracted}, engine)

# Step 3: Summarize
summary = run_prompt(summarize_prompt, {"analysis": analysis}, engine)
```

## Input Validation

PromptKit uses Pydantic-style type annotations for validation:

### Basic Types

```yaml
input_schema:
  name: str           # Required string
  age: int            # Required integer
  score: float        # Required float
  active: bool        # Required boolean
```

### Optional Types

```yaml
input_schema:
  name: str                    # Required
  middle_name: "str | None"    # Optional string
  nickname: "str | None"       # Optional string
```

### Complex Types

```yaml
input_schema:
  tags: "list[str]"                    # List of strings
  metadata: "dict[str, Any]"           # Dictionary
  coordinates: "tuple[float, float]"   # Tuple of two floats
  user_info: "dict[str, str | int]"    # Dict with string keys, string or int values
```

### Custom Validation

For complex validation, you can use Pydantic models:

```python
from pydantic import BaseModel, validator
from typing import List, Optional

class UserProfile(BaseModel):
    email: str
    age: int
    tags: List[str]

    @validator('email')
    def email_must_be_valid(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v

    @validator('age')
    def age_must_be_reasonable(cls, v):
        if v < 0 or v > 150:
            raise ValueError('Invalid age')
        return v
```

## Template Engine (Jinja2)

PromptKit uses Jinja2 for powerful templating:

### Variables

```jinja2
Hello {{ name }}!
Your score is {{ score }}.
```

### Conditionals

```jinja2
{% if user.is_premium %}
Welcome to our premium service!
{% else %}
Consider upgrading to premium.
{% endif %}
```

### Loops

```jinja2
Your items:
{% for item in items %}
- {{ item.name }}: ${{ item.price }}
{% endfor %}
```

### Filters

```jinja2
{{ message | upper }}                    {# HELLO WORLD #}
{{ tags | join(", ") }}                  {# tag1, tag2, tag3 #}
{{ price | round(2) }}                   {# 19.99 #}
{{ description | truncate(100) }}        {# First 100 chars... #}
```

### Default Values

```jinja2
Hello {{ name | default("Guest") }}!
Priority: {{ priority | default("normal") | upper }}
```

## Error Handling

PromptKit provides structured error handling:

### Validation Errors

```python
from promptkit.exceptions import ValidationError

try:
    prompt = load_prompt("my_prompt.yaml")
    result = run_prompt(prompt, invalid_data, engine)
except ValidationError as e:
    print(f"Input validation failed: {e}")
    # Handle missing or invalid inputs
```

### Template Errors

```python
from promptkit.exceptions import TemplateError

try:
    rendered = prompt.render(variables)
except TemplateError as e:
    print(f"Template rendering failed: {e}")
    # Handle undefined variables or syntax errors
```

### Engine Errors

```python
from promptkit.exceptions import EngineError

try:
    response = engine.generate(prompt_text)
except EngineError as e:
    print(f"LLM execution failed: {e}")
    # Handle API errors, rate limits, etc.
```

## Best Practices

### 1. Organize Prompts by Domain

```
prompts/
├── customer_service/
│   ├── greeting.yaml
│   ├── escalation.yaml
│   └── followup.yaml
├── content/
│   ├── blog_post.yaml
│   ├── social_media.yaml
│   └── email.yaml
└── analysis/
    ├── sentiment.yaml
    ├── summarization.yaml
    └── classification.yaml
```

### 2. Use Clear Naming

```yaml
# Good
name: customer_support_escalation_email
description: Generate escalation emails for complex customer issues

# Avoid
name: email_v2
description: Email thing
```

### 3. Design for Reusability

```yaml
# Generic prompt that works for multiple use cases
name: professional_email
description: Generate professional emails with customizable tone and purpose
template: |
  Subject: {{ subject }}

  Dear {{ recipient }},

  I hope this email finds you well. I am writing to {{ purpose }}.

  {% if tone == "formal" %}
  I would appreciate your consideration of this matter.
  {% elif tone == "friendly" %}
  I'd love to hear your thoughts on this!
  {% endif %}

  Best regards,
  {{ sender }}

input_schema:
  recipient: str
  sender: str
  subject: str
  purpose: str
  tone: "str | None"  # "formal", "friendly", "neutral"
```

### 4. Version Your Prompts

```yaml
name: code_review_v2
description: Enhanced code review with security focus (version 2.0)
# Keep old versions for backward compatibility
```

### 5. Test Thoroughly

```python
def test_greeting_prompt():
    prompt = load_prompt("greeting.yaml")

    # Test required inputs
    result = prompt.render({"name": "Alice"})
    assert "Alice" in result

    # Test optional inputs
    result = prompt.render({"name": "Bob", "context": "birthday"})
    assert "Bob" in result
    assert "birthday" in result

    # Test validation
    with pytest.raises(ValidationError):
        prompt.render({})  # Missing required 'name'
```

## Performance Considerations

### Template Compilation

Templates are compiled once and reused:

```python
# Efficient - template compiled once
prompt = load_prompt("my_prompt.yaml")
for data in batch_data:
    result = prompt.render(data)
```

### Engine Reuse

Reuse engine instances to avoid connection overhead:

```python
# Create once
engine = OpenAIEngine(api_key="sk-...")

# Use many times
for prompt_data in batch:
    result = run_prompt(prompt, prompt_data, engine)
```

### Caching

For expensive operations, consider caching:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_prompt(prompt_name):
    return load_prompt(f"{prompt_name}.yaml")
```

This foundation will help you build sophisticated, maintainable prompt-driven applications with PromptKit!
