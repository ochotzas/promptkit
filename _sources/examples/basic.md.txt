# Basic Examples

## Simple Greeting

```yaml
name: greeting
description: Generate a personalized greeting
template: |
  Hello {{ name }}! Welcome to {{ platform }}.

input_schema:
  name: str
  platform: str
```

```python
from promptkit import load_prompt, run_prompt, OpenAIEngine

prompt = load_prompt("greeting.yaml")
engine = OpenAIEngine(api_key="sk-...")
result = run_prompt(prompt, {"name": "Alice", "platform": "PromptKit"}, engine)
```

## Email Generator

```yaml
name: email
description: Generate professional emails
template: |
  Subject: {{ subject }}

  Dear {{ recipient }},

  {{ body }}
  
  {% if next_steps %}
  Next steps: {{ next_steps }}
  {% endif %}

  Best regards,
  {{ sender }}

input_schema:
  recipient: str
  sender: str
  subject: str
  body: str
  next_steps: "str | None"
```

## Blog Outline

```yaml
name: blog_outline
description: Create blog post outline
template: |
  # {{ title }}

  Target: {{ audience }}
  
  ## Sections
  {% for section in sections %}
  ### {{ loop.index }}. {{ section }}
  {% endfor %}
  
  Keywords: {{ keywords | join(", ") }}

input_schema:
  title: str
  audience: str
  sections: list
  keywords: list
```

## FAQ Response

```yaml
name: faq
description: Generate FAQ responses
template: |
  **Q: {{ question }}**

  {{ answer }}
  
  {% if steps %}
  Steps:
  {% for step in steps %}
  {{ loop.index }}. {{ step }}
  {% endfor %}
  {% endif %}

input_schema:
  question: str
  answer: str
  steps: "list | None"
```
