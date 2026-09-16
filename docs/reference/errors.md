# Errors

Every exception raised out of PromptKit descends from `PromptKitError`. No third-party
exception reaches you from the public API.

```
PromptKitError
├── PromptError
│   ├── PromptNotFoundError      also a FileNotFoundError
│   ├── PromptParseError         also a yaml.YAMLError and ValueError
│   ├── TemplateError            also a jinja2.TemplateError
│   └── SchemaError              also a ValueError
├── ValidationError              also a ValueError
│   ├── InputValidationError
│   └── OutputValidationError
├── EngineError
│   ├── EngineNotFoundError
│   ├── AuthenticationError
│   ├── RateLimitError
│   ├── ModelNotFoundError
│   ├── ContextLengthError
│   └── ProviderError
└── EvalError
```

Several types also subclass the standard exception they replace, so existing
`except FileNotFoundError` and `except ValueError` handlers keep working.

## Attributes

Exceptions carry structured detail, not just a message.

| Type | Attributes |
| --- | --- |
| `PromptNotFoundError` | `path` |
| `PromptParseError` | `path`, `missing_fields` |
| `TemplateError` | `template_name` |
| `SchemaError` | `field` |
| `ValidationError` | `cause`, `errors()` |
| `EngineError` | `model` |
| `EngineNotFoundError` | `name`, `install_hint` |
| `RateLimitError` | `retry_after` |
| `ProviderError` | `status_code`, `body` |

```python
from promptkit.errors import PromptParseError, RateLimitError

try:
    prompt = load_prompt("greet.yaml")
except PromptParseError as e:
    print(e.path, e.missing_fields)

try:
    engine.complete("...")
except RateLimitError as e:
    sleep(e.retry_after or 5)
```

## Which ones to catch

**`PromptKitError`** at an application boundary, to turn any PromptKit failure into your
own error response.

**`InputValidationError`** when inputs come from users. `errors()` forwards Pydantic's
structured detail, suitable for a form response:

```python
except InputValidationError as e:
    return {"errors": [{"field": p["loc"], "message": p["msg"]} for p in e.errors()]}
```

**`RateLimitError`** only if you have disabled the built-in retry. By default it is
already retried with backoff.

**`EngineNotFoundError`** when an engine name comes from configuration. Its message
names the exact `pip install`.

## Provider mapping

Each engine maps its SDK's exceptions onto this hierarchy, so provider-independent code
is possible:

```python
try:
    completion = engine.complete(messages)
except AuthenticationError:
    ...  # 401/403, whichever provider
except ContextLengthError:
    ...  # prompt too long, whichever provider
except ProviderError as e:
    ...  # e.status_code when there was one
```

An exception an engine does not recognise is re-raised unchanged rather than being
flattened into `ProviderError` — an unexpected error should look unexpected.
