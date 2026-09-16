# Schemas

PromptKit validates inputs before rendering and can validate outputs after generation.
There are three ways to describe a schema, and they exist for different audiences.

## Type strings

The terse form, for the common case:

```yaml
input_schema:
  name: str
  age: int
  score: float
  active: bool
  tags: list
  extra: dict
  email: "str | None"
```

Append `| None` to make a field optional. Quote it — YAML would otherwise read the
`|` as a block scalar.

**The type-string language is frozen.** Those six scalars plus `| None` are all it will
ever parse. It will not grow `list[str]`, constrained forms, or enums. Anything else
raises `SchemaError` naming the field and pointing here:

```
SchemaError: Unsupported type 'list[str]' for field 'tags'. The type-string language
is frozen at: bool, dict, float, int, list, str (append ' | None' for optional).
For anything richer, use a JSON Schema object instead.
```

This is deliberate. A half-built type language is worse than delegating to one that
already works.

## JSON Schema

For anything richer, put a JSON Schema object in `input_schema` instead:

```yaml
input_schema:
  type: object
  required: [name, tags]
  properties:
    name:
      type: string
      description: Customer name
    tags:
      type: array
      items:
        type: string
    tier:
      enum: [free, pro, enterprise]
    address:
      type: object
      properties:
        city: { type: string }
        country: { type: string }
      required: [city]
```

Supported: `object`, `array`, `string`, `integer`, `number`, `boolean`, `null`,
`properties`, `required`, `items`, `enum`, `default`, `description`, type unions
(`"type": ["string", "null"]`), and local `$ref` into `$defs` or `definitions`.

Anything unsupported raises `SchemaError` naming the construct.

### How the two forms are told apart

A schema is read as JSON Schema when it has a `properties` key, a `$schema` key, or a
`type` whose value is a real JSON Schema type name. So `{"type": "str"}` is still a
type-string mapping with a field called `type` — `str` is not a JSON Schema type.

## Pydantic models

From Python, skip both and hand over a model:

```python
from pydantic import BaseModel
from promptkit import run_structured

class Invoice(BaseModel):
    number: str
    total: float

result = run_structured(prompt, {"document": text}, engine, output_model=Invoice)
result.value.total   # a float, and your type checker knows it
```

This is the recommended path for typed applications. No string-based schema can give you
an inferred result type.

## Output schemas

`output_schema` takes JSON Schema only, and must describe an object:

```yaml
output_schema:
  type: object
  required: [invoice_number, total]
  properties:
    invoice_number: { type: string }
    total: { type: number }
    currency:
      type: string
      enum: [USD, EUR, GBP]
```

See [structured output](structured-output.md) for how it is enforced.

## Validation errors

Input validation raises `InputValidationError`, which subclasses `ValueError` and
forwards Pydantic's structured detail:

```python
from promptkit.errors import InputValidationError

try:
    prompt.render({"age": "not a number"})
except InputValidationError as e:
    for problem in e.errors():
        print(problem["loc"], problem["msg"])
```

Skip validation with `prompt.render(inputs, validate=False)` when you have already
validated upstream.
