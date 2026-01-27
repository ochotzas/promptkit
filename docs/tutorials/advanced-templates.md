# Advanced Templates

PromptKit uses Jinja2 for templating.

## Conditionals

```yaml
template: |
  {% if user_type == "beginner" %}
  Simple explanation: {{ explanation }}
  {% elif user_type == "expert" %}
  Technical details: {{ technical }}
  {% else %}
  Balanced view: {{ balanced }}
  {% endif %}
```

## Loops

```yaml
template: |
  Items:
  {% for item in items %}
  {{ loop.index }}. {{ item.name }}: {{ item.description }}
  {% if item.priority == "high" %}⚠️ HIGH{% endif %}
  {% endfor %}
  
  Total: {{ items | length }}
```

## Filters

```yaml
template: |
  Title: {{ title | title }}
  Tags: {{ tags | join(", ") }}
  Content: {{ content | truncate(100) }}
  
  {% for item in items | sort(attribute="score") | reverse %}
  - {{ item.name }}
  {% endfor %}
```

## Default Values

```yaml
template: |
  Hello {{ name | default("there") }}!
  Priority: {{ priority | default("normal") | upper }}
```

## Macros

```yaml
template: |
  {% macro format_user(user) %}
  Name: {{ user.name }}
  Role: {{ user.role }}
  {% endmacro %}
  
  {% for user in users %}
  {{ format_user(user) }}
  {% endfor %}
```

## Whitespace Control

```yaml
template: |
  {%- if condition -%}
  No extra whitespace
  {%- endif -%}
```

## Error Handling

```yaml
template: |
  {% if items %}
  {% for item in items %}
  - {{ item }}
  {% endfor %}
  {% else %}
  No items found.
  {% endif %}
```
