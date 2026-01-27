# Input Validation

PromptKit uses Pydantic for input validation.

## Basic Types

```yaml
input_schema:
  name: str
  age: int
  score: float
  active: bool
```

## Optional Fields

Use `| None` for optional fields:

```yaml
input_schema:
  name: str
  email: "str | None"
```

## Collection Types

```yaml
input_schema:
  tags: list
  metadata: dict
```

## Validation Example

```python
from promptkit import Prompt

prompt = Prompt(
    name="test",
    description="Test",
    template="Hello {{ name }}, age {{ age }}",
    input_schema={"name": "str", "age": "int"}
)

# Valid
result = prompt.render({"name": "Alice", "age": 30})

# Invalid - raises ValidationError
prompt.render({"name": "Alice", "age": "thirty"})

# Invalid - raises ValidationError (missing required field)
prompt.render({"name": "Alice"})
```

## Optional Fields

```python
prompt = Prompt(
    name="test",
    description="Test",
    template="Hello {{ name }}{% if email %}, {{ email }}{% endif %}",
    input_schema={"name": "str", "email": "str | None"}
)

# Both valid
prompt.render({"name": "Alice", "email": "alice@example.com"})
prompt.render({"name": "Alice"})
```

## Get Field Info

```python
prompt = Prompt(
    name="test",
    description="Test",
    template="...",
    input_schema={"name": "str", "email": "str | None"}
)

required = prompt.get_required_inputs()  # ["name"]
optional = prompt.get_optional_inputs()  # ["email"]
```
