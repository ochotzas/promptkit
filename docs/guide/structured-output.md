# Structured output

Ask for JSON, get a validated object back.

## Declaring the shape

In the prompt file:

```yaml
name: extract_invoice
description: Extracts structured invoice fields from raw text
version: 1.0.0
messages:
  - role: system
    template: Extract invoice fields. Return only the requested fields.
  - role: user
    template: "{{ document }}"
input_schema:
  document: str
output_schema:
  type: object
  required: [invoice_number, total, currency]
  properties:
    invoice_number: { type: string }
    total: { type: number }
    currency:
      type: string
      enum: [USD, EUR, GBP]
```

```python
from promptkit import load_prompt, run_structured

prompt = load_prompt("extract_invoice.yaml")
result = run_structured(prompt, {"document": raw_text}, engine)

result.value.invoice_number   # validated
result.completion.usage       # the underlying Completion
```

## Or a Pydantic model

```python
from pydantic import BaseModel

class Invoice(BaseModel):
    invoice_number: str
    total: float
    currency: str

result = run_structured(prompt, {"document": raw_text}, engine, output_model=Invoice)
```

This is the better path in typed code: `result.value` is an `Invoice`, and your type
checker knows it. An explicit `output_model` overrides the prompt's `output_schema`.

## What happens

1. If the engine advertises `json_mode`, the schema is sent as a native
   structured-output request.
2. Otherwise a schema instruction is appended as a final system message.
3. The response is parsed. JSON is recovered from bare output, fenced blocks, and JSON
   embedded in prose.
4. On a parse or validation failure, the model is re-prompted with its previous answer
   and the exact error, up to `max_parse_retries` (default 2).

Each retry emits a `ParseRetried` event.

```python
result = run_structured(
    prompt, inputs, engine, output_model=Invoice, max_parse_retries=4
)
```

Set `max_parse_retries=0` to fail on the first bad response.

## When it gives up

```python
from promptkit.errors import OutputValidationError

try:
    result = run_structured(prompt, inputs, engine, output_model=Invoice)
except OutputValidationError as e:
    print(e)          # what was wrong
    print(e.errors()) # Pydantic's structured detail, when the failure was validation
```

## Async

```python
result = await run_structured_async(prompt, inputs, engine, output_model=Invoice)
```

## Notes

- `output_schema` must describe an object. A top-level array is rejected at load.
- `AnthropicEngine` does not advertise `json_mode`, so it uses the instruction path.
  Anthropic's native structured output is tool-shaped, and tool calling is
  [out of scope](../scope.md).
- Retries cost tokens. The repair message includes the previous answer, so a retry is
  more expensive than the first attempt. Keep `max_parse_retries` low and your schema
  small.
