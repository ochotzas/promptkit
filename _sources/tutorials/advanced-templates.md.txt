# Advanced Template Techniques

Learn how to create sophisticated templates using PromptKit's advanced features like conditionals, loops, custom filters, and template inheritance.

## Overview

PromptKit uses Jinja2 as its templating engine, which provides powerful features for creating dynamic and reusable prompts. This guide covers advanced techniques beyond basic variable substitution.

## Conditional Logic

Use conditional statements to create adaptive prompts:

```yaml
name: adaptive_response
description: Response that adapts based on user type
template: |
  {% if user_type == "beginner" %}
  Let me explain this in simple terms:
  {{ explanation_simple }}
  {% elif user_type == "expert" %}
  Technical details:
  {{ explanation_technical }}
  {% else %}
  Here's a balanced explanation:
  {{ explanation_balanced }}
  {% endif %}
input_schema:
  user_type: str
  explanation_simple: str
  explanation_technical: str
  explanation_balanced: str
```

## Loops and Iteration

Process lists and create dynamic content:

```yaml
name: process_items
description: Process a list of items
template: |
  Here are the items to process:
  {% for item in items %}
  {{ loop.index }}. {{ item.name }}: {{ item.description }}
  {% if item.priority == "high" %}⚠️ HIGH PRIORITY{% endif %}
  {% endfor %}

  Summary: {{ items|length }} items total
input_schema:
  items:
    type: array
    items:
      type: object
      properties:
        name: str
        description: str
        priority: str
```

## Template Filters

Use built-in and custom filters to transform data:

```yaml
name: formatted_content
description: Content with various formatting
template: |
  Title: {{ title|title }}
  Date: {{ date|strftime('%Y-%m-%d') }}
  Tags: {{ tags|join(', ') }}
  Content: {{ content|truncate(100) }}

  {% if items %}
  Top Items:
  {% for item in items|sort(attribute='score')|reverse|list[:3] %}
  - {{ item.name }} (Score: {{ item.score }})
  {% endfor %}
  {% endif %}
input_schema:
  title: str
  date: str
  tags:
    type: array
    items: str
  content: str
  items:
    type: array
    items:
      type: object
      properties:
        name: str
        score: int
```

## Template Inheritance

Create reusable template bases:

### Base Template (base_prompt.yaml)
```yaml
name: base_prompt
description: Base template for all prompts
template: |
  System: You are {{ role }}.

  Context: {{ context }}

  {% block instructions %}
  Please provide a helpful response.
  {% endblock %}

  {% block additional_info %}{% endblock %}

  User Query: {{ query }}
input_schema:
  role: str
  context: str
  query: str
```

### Child Template (specialized_prompt.yaml)
```yaml
name: specialized_prompt
description: Specialized prompt extending base
extends: base_prompt.yaml
template: |
  {% extends "base_prompt.yaml" %}

  {% block instructions %}
  Please provide a detailed technical analysis including:
  1. Problem identification
  2. Solution approach
  3. Implementation steps
  4. Potential risks
  {% endblock %}

  {% block additional_info %}
  Technical Level: {{ technical_level }}
  Domain: {{ domain }}
  {% endblock %}
input_schema:
  role: str
  context: str
  query: str
  technical_level: str
  domain: str
```

## Macros for Reusability

Define reusable template components:

```yaml
name: prompt_with_macros
description: Prompt using macros for reusable components
template: |
  {% macro format_user(user) %}
  Name: {{ user.name }}
  Role: {{ user.role }}
  {% if user.expertise %}Expertise: {{ user.expertise }}{% endif %}
  {% endmacro %}

  {% macro format_task(task, show_priority=True) %}
  Task: {{ task.title }}
  Description: {{ task.description }}
  {% if show_priority and task.priority %}Priority: {{ task.priority }}{% endif %}
  {% endmacro %}

  Project Briefing:

  Team Members:
  {% for user in team %}
  {{ format_user(user) }}
  {% endfor %}

  Tasks:
  {% for task in tasks %}
  {{ format_task(task) }}
  {% endfor %}
input_schema:
  team:
    type: array
    items:
      type: object
      properties:
        name: str
        role: str
        expertise: str
  tasks:
    type: array
    items:
      type: object
      properties:
        title: str
        description: str
        priority: str
```

## Error Handling in Templates

Handle missing or invalid data gracefully:

```yaml
name: robust_prompt
description: Prompt with error handling
template: |
  Welcome {{ user.name|default("Guest") }}!

  {% if user.preferences %}
  Your preferences:
  {% for pref in user.preferences %}
  - {{ pref|title }}
  {% endfor %}
  {% else %}
  No preferences set. Using defaults.
  {% endif %}

  {% try %}
  Account Status: {{ user.account.status|upper }}
  Last Login: {{ user.account.last_login|strftime('%Y-%m-%d') }}
  {% except %}
  Account information unavailable.
  {% endtry %}

  {% set item_count = items|length if items else 0 %}
  You have {{ item_count }} item{{ 's' if item_count != 1 else '' }}.
input_schema:
  user:
    type: object
    properties:
      name: str
      preferences:
        type: array
        items: str
      account:
        type: object
        properties:
          status: str
          last_login: str
  items:
    type: array
    items: object
```

## Custom Template Functions

Extend templates with custom functions:

```python
# In your Python code
from promptkit.core.loader import load_prompt
from promptkit.core.template import TemplateRenderer

def custom_format_currency(amount, currency="USD"):
    """Custom function to format currency"""
    return f"{currency} {amount:,.2f}"

def custom_pluralize(count, singular, plural=None):
    """Custom pluralization function"""
    if plural is None:
        plural = singular + "s"
    return singular if count == 1 else plural

# Register custom functions
renderer = TemplateRenderer()
renderer.add_function("format_currency", custom_format_currency)
renderer.add_function("pluralize", custom_pluralize)

# Use in templates
prompt = load_prompt("financial_report.yaml")
result = renderer.render(prompt.template, {
    "revenue": 150000.50,
    "expense_count": 5
}, functions={
    "format_currency": custom_format_currency,
    "pluralize": custom_pluralize
})
```

Template with custom functions:
```yaml
name: financial_report
description: Financial report with custom formatting
template: |
  Financial Summary:
  Revenue: {{ format_currency(revenue) }}

  We processed {{ expense_count }} {{ pluralize(expense_count, "expense") }} this month.
input_schema:
  revenue: float
  expense_count: int
```

## Best Practices

1. **Keep templates readable**: Use proper indentation and comments
2. **Validate inputs**: Always define comprehensive input schemas
3. **Handle edge cases**: Use default values and error handling
4. **Modularize with macros**: Create reusable components
5. **Test thoroughly**: Test templates with various input combinations
6. **Document complex logic**: Add comments for complex template logic

## Performance Considerations

- Use `{% set %}` to avoid repeated calculations
- Minimize complex operations in loops
- Cache rendered templates when possible
- Use `{% raw %}` blocks for literal Jinja2 syntax

## Common Patterns

### Multi-language Support
```yaml
name: multilingual_prompt
description: Prompt supporting multiple languages
template: |
  {% set messages = {
    'en': {'greeting': 'Hello', 'farewell': 'Goodbye'},
    'es': {'greeting': 'Hola', 'farewell': 'Adiós'},
    'fr': {'greeting': 'Bonjour', 'farewell': 'Au revoir'}
  } %}

  {{ messages[language]['greeting'] }} {{ name }}!

  {{ content }}

  {{ messages[language]['farewell'] }}!
input_schema:
  language: str
  name: str
  content: str
```

### Dynamic Validation
```yaml
name: dynamic_validation
description: Prompt with dynamic validation rules
template: |
  {% if validation_level == "strict" %}
  Please ensure your response meets these criteria:
  {% for rule in strict_rules %}
  - {{ rule }}
  {% endfor %}
  {% elif validation_level == "moderate" %}
  Consider these guidelines:
  {% for rule in moderate_rules %}
  - {{ rule }}
  {% endfor %}
  {% endif %}

  Query: {{ query }}
input_schema:
  validation_level: str
  strict_rules:
    type: array
    items: str
  moderate_rules:
    type: array
    items: str
  query: str
```

This guide provides a comprehensive overview of advanced templating techniques in PromptKit. Use these patterns to create sophisticated, maintainable, and reusable prompts.
