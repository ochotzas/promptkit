# Creating Your First Prompt

Build a code review prompt from scratch.

## Design

A code review prompt needs:
- Code snippet input
- Programming language
- Review style option

## Create the YAML

Create `code_review.yaml`:

```yaml
name: code_review
description: AI-powered code review
template: |
  Review the following {{ language }} code:

  ```{{ language }}
  {{ code }}
  ```
  
  {% if style == "strict" %}
  Focus on bugs, performance, and style violations. Be critical.
  {% elif style == "security" %}
  Focus on security vulnerabilities and attack vectors.
  {% else %}
  Provide helpful feedback on readability and best practices.
  {% endif %}
  
  Format your review as:
  - **Summary**: Overall assessment
  - **Issues**: Problems found
  - **Suggestions**: Improvements

input_schema:
  code: str
  language: str
  style: "str | None"
```

## Use in Python

```python
from promptkit import load_prompt, run_prompt, OpenAIEngine

prompt = load_prompt("code_review.yaml")

code = """
def calculate(items):
    total = 0
    for item in items:
        total += item.price
    return total
"""

engine = OpenAIEngine(api_key="sk-...")
review = run_prompt(
    prompt,
    {"code": code, "language": "python", "style": "helpful"},
    engine
)
print(review)
```

## Use the CLI

```bash
# Render to preview
promptkit render code_review.yaml \
  --vars '{"code": "def hello(): pass", "language": "python"}'

# Validate
promptkit lint code_review.yaml

# Get info
promptkit info code_review.yaml
```

## Best Practices

### Clear Schema

```yaml
input_schema:
  user_id: str                  # Required
  preferences: "list | None"    # Optional
```

### Default Values

Use Jinja2 filters:

```yaml
template: |
  Hello {{ name | default("there") }}!
  Priority: {{ priority | default("normal") }}
```

### Conditional Logic

```yaml
template: |
  {% if detailed %}
  Provide comprehensive analysis.
  {% else %}
  Provide brief summary.
  {% endif %}
```
