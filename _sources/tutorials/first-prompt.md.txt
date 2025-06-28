# Creating Your First Prompt

This tutorial will guide you through creating a more sophisticated prompt from scratch, covering best practices and common patterns.

## What We'll Build

We'll create a code review prompt that:
- Takes code snippets as input
- Allows customizable review criteria
- Provides structured feedback
- Demonstrates advanced templating

## Step 1: Design the Prompt

Let's think about what our code review prompt needs:

- **Input**: Code snippet, programming language, focus areas
- **Output**: Structured review with suggestions
- **Flexibility**: Different review styles (strict, helpful, security-focused)

## Step 2: Create the YAML File

Create `code_review.yaml`:

````yaml
name: code_review
description: AI-powered code review with customizable focus areas
template: |
  Please review the following {{ language }} code:

  ```{{ language }}
  {{ code }}
  ```

  ## Review Criteria
  {% if style == "strict" %}
  Focus on potential bugs, performance issues, and code style violations.
  Be thorough and critical.
  {% elif style == "security" %}
  Focus specifically on security vulnerabilities, input validation, and potential attack vectors.
  {% else %}
  Provide helpful, constructive feedback focusing on readability and best practices.
  {% endif %}

  {% if focus_areas %}
  Pay special attention to:
  {% for area in focus_areas %}
  - {{ area }}
  {% endfor %}
  {% endif %}

  ## Required Output Format
  Please structure your review as:

  **Summary**: Brief overall assessment
  **Issues Found**: List specific problems with line numbers if applicable
  **Suggestions**: Concrete improvement recommendations
  **Rating**: Score from 1-10 with justification

input_schema:
  code: str
  language: str
  style: "str | None"
  focus_areas: "list[str] | None"
````

## Step 3: Test the Prompt

### Using Python

```python
from promptkit.core.loader import load_prompt
from promptkit.core.runner import run_prompt
from promptkit.engines.openai import OpenAIEngine

# Load the prompt
prompt = load_prompt("code_review.yaml")

# Test data
code_sample = '''
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total
'''

# Create input data
review_data = {
    "code": code_sample,
    "language": "python",
    "style": "helpful",
    "focus_areas": ["error handling", "type hints"]
}

# Run the review
engine = OpenAIEngine()
review = run_prompt(prompt, review_data, engine)
print(review)
```

### Using the CLI

```bash
# Interactive mode - you'll be prompted for missing inputs
promptkit run code_review.yaml

# Provide all inputs via CLI
promptkit run code_review.yaml \
  --code "def hello(): print('world')" \
  --language python \
  --style helpful
```

## Step 4: Advanced Features

### Template Rendering Only

Sometimes you want to see the rendered prompt without calling an AI:

```bash
promptkit render code_review.yaml \
  --code "def hello(): print('world')" \
  --language python \
  --style strict
```

### Validation and Debugging

```bash
# Check prompt structure
promptkit lint code_review.yaml

# Get detailed prompt information
promptkit info code_review.yaml

# Estimate costs before running
promptkit cost code_review.yaml --model gpt-4
```

## Step 5: Iteration and Improvement

### Version 2: Enhanced Prompt

````yaml
name: code_review_v2
description: Enhanced code review with context awareness
template: |
  You are an expert {{ language }} developer reviewing code for a {{ project_type }} project.

  **Code to Review:**
  ```{{ language }}
  {{ code }}
  ```

  **Context:**
  - Project type: \{\{ project_type \}\}
  - Team experience: \{\{ team_level | default("mixed") \}\}
  - {% if deadline %}Deadline pressure: \{\{ deadline \}\}{% endif %}

  **Review Style:** {{ style | default("balanced") }}
  {% if style == "mentoring" %}
  Focus on teaching opportunities and explaining why changes are needed.
  {% elif style == "production" %}
  Focus on code that will go to production - prioritize reliability and maintainability.
  {% endif %}

  Please provide a comprehensive review following our standard format.

input_schema:
  code: str
  language: str
  project_type: str
  team_level: "str | None"
  deadline: "str | None"
  style: "str | None"
````

## Best Practices

### 1. Clear Input Schema

```yaml
input_schema:
  # Always include helpful comments in your schema
  user_id: str                    # Required: User identifier
  preferences: "list[str] | None" # Optional: User preferences
  metadata: "dict[str, Any]"      # Flexible: Additional context
```

### 2. Default Values

Use Jinja2 filters for graceful defaults:

```yaml
template: |
  Hello {{ name | default("there") }}!
  Priority: {{ priority | default("normal") | upper }}
```

### 3. Conditional Logic

Structure complex logic clearly:

```yaml
template: |
  {% if user_type == "premium" %}
    Welcome to our premium experience!
  {% elif user_type == "trial" %}
    You have {{ days_left }} days remaining in your trial.
  {% else %}
    Consider upgrading for more features!
  {% endif %}
```

### 4. Error Handling

Always validate your prompts:

```python
from promptkit.core.loader import load_prompt
from promptkit.exceptions import ValidationError

try:
    prompt = load_prompt("my_prompt.yaml")
    # Test with sample data
    result = prompt.render({"test": "data"})
except ValidationError as e:
    print(f"Prompt validation failed: {e}")
```

## Common Patterns

### Multi-step Workflows

```python
# Load multiple related prompts
analyze_prompt = load_prompt("analyze_code.yaml")
summarize_prompt = load_prompt("summarize_analysis.yaml")

# Chain them together
analysis = run_prompt(analyze_prompt, code_data, engine)
summary = run_prompt(summarize_prompt, {"analysis": analysis}, engine)
```

### Dynamic Prompt Selection

```python
def get_review_prompt(experience_level):
    if experience_level == "beginner":
        return load_prompt("review_beginner.yaml")
    elif experience_level == "expert":
        return load_prompt("review_expert.yaml")
    else:
        return load_prompt("review_standard.yaml")
```

## Next Steps

Now that you've created your first prompt, explore:

- [Advanced Templates](advanced-templates.md) - Complex Jinja2 patterns
- [Input Validation](validation.md) - Schema design best practices
- [Basic Examples](../examples/basic.md) - More prompt examples
- [API Reference](../api/core.md) - Complete API documentation

You're well on your way to mastering PromptKit!
