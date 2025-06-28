# Basic Examples

This page provides a collection of basic prompt examples to help you get started with common use cases.

## Simple Text Generation

### Basic Greeting

```yaml
name: simple_greeting
description: Generate a personalized greeting
template: |
  Hello {{ name }}! Welcome to {{ platform }}.

input_schema:
  name: str
  platform: str
```

**Usage:**
```python
from promptkit.core.loader import load_prompt
from promptkit.engines.openai import OpenAIEngine

prompt = load_prompt("simple_greeting.yaml")
engine = OpenAIEngine()

result = run_prompt(prompt, {
    "name": "Alice",
    "platform": "PromptKit"
}, engine)
```

### Email Generator

```yaml
name: email_generator
description: Generate professional emails
template: |
  Subject: {{ subject }}

  Dear {{ recipient }},

  I hope this email finds you well. I am writing to {{ purpose }}.

  {% if details %}
  Here are the key details:
  {{ details }}
  {% endif %}

  {% if next_steps %}
  Next steps:
  {{ next_steps }}
  {% endif %}

  Best regards,
  {{ sender }}

input_schema:
  recipient: str
  sender: str
  subject: str
  purpose: str
  details: "str | None"
  next_steps: "str | None"
```

## Content Creation

### Blog Post Outline

```yaml
name: blog_outline
description: Create a structured blog post outline
template: |
  # {{ title }}

  **Target Audience:** {{ audience }}
  **Estimated Reading Time:** {{ reading_time }} minutes

  ## Introduction
  Hook the reader with {{ hook_type }} and introduce the main topic.

  ## Main Sections
  {% for section in sections %}
  ### {{ loop.index }}. {{ section }}
  - Key points to cover
  - Supporting examples
  {% endfor %}

  ## Conclusion
  Summarize key takeaways and include a call-to-action.

  **SEO Keywords:** {{ keywords | join(", ") }}

input_schema:
  title: str
  audience: str
  reading_time: int
  hook_type: str
  sections: "list[str]"
  keywords: "list[str]"
```

### Product Description

```yaml
name: product_description
description: Generate compelling product descriptions
template: |
  ## {{ product_name }}

  {{ tagline }}

  **Price:** ${{ price }}
  **Category:** {{ category }}

  ### Key Features
  {% for feature in features %}
  - **{{ feature.name }}**: {{ feature.description }}
  {% endfor %}

  ### Perfect For
  This product is ideal for {{ target_audience }} who want {{ primary_benefit }}.

  {% if specifications %}
  ### Specifications
  {% for spec, value in specifications.items() %}
  - **{{ spec }}**: {{ value }}
  {% endfor %}
  {% endif %}

  ### Why Choose {{ product_name }}?
  {{ unique_selling_point }}

input_schema:
  product_name: str
  tagline: str
  price: float
  category: str
  features: "list[dict[str, str]]"
  target_audience: str
  primary_benefit: str
  specifications: "dict[str, str] | None"
  unique_selling_point: str
```

## Question Answering

### FAQ Response

```yaml
name: faq_response
description: Generate helpful FAQ responses
template: |
  **Question:** {{ question }}

  **Answer:**

  {{ answer_intro }}

  {% if steps %}
  Here's how to {{ action_verb }}:

  {% for step in steps %}
  {{ loop.index }}. {{ step }}
  {% endfor %}
  {% endif %}

  {% if additional_info %}
  **Additional Information:**
  {{ additional_info }}
  {% endif %}

  {% if related_topics %}
  **Related Topics:**
  {% for topic in related_topics %}
  - {{ topic }}
  {% endfor %}
  {% endif %}

input_schema:
  question: str
  answer_intro: str
  action_verb: "str | None"
  steps: "list[str] | None"
  additional_info: "str | None"
  related_topics: "list[str] | None"
```

## Data Processing

### Report Summary

```yaml
name: report_summary
description: Summarize data reports with key insights
template: |
  # {{ report_title }} - Executive Summary

  **Report Period:** {{ start_date }} to {{ end_date }}
  **Generated:** {{ generation_date }}

  ## Key Metrics
  {% for metric in key_metrics %}
  - **{{ metric.name }}**: {{ metric.value }} {{ metric.unit }}
    {% if metric.change %}({{ metric.change }}% {{ "increase" if metric.change > 0 else "decrease" }} from last period){% endif %}
  {% endfor %}

  ## Highlights
  {% for highlight in highlights %}
  - {{ highlight }}
  {% endfor %}

  ## Trends
  {% for trend in trends %}
  ### {{ trend.category }}
  {{ trend.description }}
  {% if trend.recommendation %}
  **Recommendation:** {{ trend.recommendation }}
  {% endif %}
  {% endfor %}

  ## Action Items
  {% for item in action_items %}
  - [ ] {{ item.task }} (Priority: {{ item.priority }}, Due: {{ item.due_date }})
  {% endfor %}

input_schema:
  report_title: str
  start_date: str
  end_date: str
  generation_date: str
  key_metrics: "list[dict[str, Any]]"
  highlights: "list[str]"
  trends: "list[dict[str, str]]"
  action_items: "list[dict[str, str]]"
```

## Educational Content

### Study Guide

```yaml
name: study_guide
description: Create structured study guides for any topic
template: |
  # {{ subject }} Study Guide

  **Difficulty Level:** {{ level }}
  **Estimated Study Time:** {{ study_time }} hours

  ## Learning Objectives
  By the end of this study session, you should be able to:
  {% for objective in objectives %}
  - {{ objective }}
  {% endfor %}

  ## Key Concepts
  {% for concept in concepts %}
  ### {{ concept.name }}
  **Definition:** {{ concept.definition }}

  {% if concept.examples %}
  **Examples:**
  {% for example in concept.examples %}
  - {{ example }}
  {% endfor %}
  {% endif %}

  {% if concept.formula %}
  **Formula:** `{{ concept.formula }}`
  {% endif %}
  {% endfor %}

  ## Practice Questions
  {% for question in practice_questions %}
  {{ loop.index }}. {{ question.question }}
     {% if question.hint %}*Hint: {{ question.hint }}*{% endif %}
  {% endfor %}

  ## Additional Resources
  {% for resource in resources %}
  - [{{ resource.title }}]({{ resource.url }}) - {{ resource.description }}
  {% endfor %}

input_schema:
  subject: str
  level: str
  study_time: int
  objectives: "list[str]"
  concepts: "list[dict[str, Any]]"
  practice_questions: "list[dict[str, str]]"
  resources: "list[dict[str, str]]"
```

## CLI Usage Examples

### Running Basic Examples

```bash
# Simple greeting
promptkit run simple_greeting.yaml --name "John" --platform "MyApp"

# Email generation with all fields
promptkit run email_generator.yaml \
  --recipient "team@company.com" \
  --sender "Alice" \
  --subject "Project Update" \
  --purpose "provide a status update on our current project"

# Product description
promptkit render product_description.yaml \
  --vars '{"product_name": "Smart Watch", "price": 299.99, "category": "Electronics"}'
```

### Interactive Mode

When you don't provide all required inputs, PromptKit will prompt you interactively:

```bash
$ promptkit run email_generator.yaml
Missing required inputs: recipient, sender, subject, purpose
Enter value for 'recipient' (str): john@example.com
Enter value for 'sender' (str): Alice
Enter value for 'subject' (str): Meeting Follow-up
Enter value for 'purpose' (str): follow up on our discussion
```

### Cost Estimation

Check costs before running expensive prompts:

```bash
promptkit cost blog_outline.yaml --model gpt-4 \
  --title "AI in Healthcare" \
  --audience "medical professionals"
```

## Python Integration Examples

### Batch Processing

```python
from promptkit.core.loader import load_prompt
from promptkit.engines.openai import OpenAIEngine

# Load prompt once
prompt = load_prompt("product_description.yaml")
engine = OpenAIEngine()

# Process multiple products
products = [
    {"product_name": "Laptop", "price": 999.99, "category": "Electronics"},
    {"product_name": "Coffee Mug", "price": 12.99, "category": "Kitchen"},
    {"product_name": "Running Shoes", "price": 89.99, "category": "Sports"}
]

descriptions = []
for product in products:
    # Add required fields
    product.update({
        "tagline": f"Premium {product['product_name']}",
        "features": [{"name": "Quality", "description": "High-quality materials"}],
        "target_audience": "discerning customers",
        "primary_benefit": "excellent value",
        "unique_selling_point": "Unmatched quality at this price point"
    })

    description = run_prompt(prompt, product, engine)
    descriptions.append(description)
```

### Error Handling

```python
from promptkit.core.loader import load_prompt
from promptkit.exceptions import ValidationError, TemplateError

try:
    prompt = load_prompt("my_prompt.yaml")
    result = run_prompt(prompt, {"invalid": "data"}, engine)
except ValidationError as e:
    print(f"Input validation failed: {e}")
except TemplateError as e:
    print(f"Template rendering failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Next Steps

- Explore [Advanced Templates](../tutorials/advanced-templates.md) for complex Jinja2 patterns
- Learn about [Input Validation](../tutorials/validation.md) for robust schema design
- Check out [Advanced Examples](advanced.md) for more sophisticated use cases
- Review the [API Reference](../api/core.md) for complete documentation
