# Python API

Everything exported from `promptkit` is public and covered by the
[compatibility contract](#compatibility). Anything else is internal.

## Loading

```python
from promptkit import load_prompt, loads_prompt, save_prompt, PromptRegistry
```

| | |
| --- | --- |
| `load_prompt(path, root=None)` | Load a prompt file. Extension optional. `root` widens the include search path |
| `loads_prompt(text, source="<string>")` | Load from a YAML string |
| `save_prompt(prompt, path)` | Write a prompt back to YAML |
| `PromptRegistry(root)` | Directory-backed registry with dotted names |

`PromptRegistry` supports `get(name)`, `names()`, `all()`, `partials()`, `resolve(name)`,
`clear_cache()`, plus `in`, `len()`, iteration, and `registry["name"]`. Entries are
cached and invalidated by mtime.

## Prompt

```python
from promptkit import Prompt, MessageTemplate, PromptMetadata
```

| Attribute | Type |
| --- | --- |
| `name` | `str` |
| `description` | `str` |
| `version` | `str` — advisory, not identity |
| `messages` | `tuple[MessageTemplate, ...]` |
| `input_schema` | `dict[str, Any]` — type strings or JSON Schema |
| `output_schema` | `dict[str, Any] | None` |
| `metadata` | `PromptMetadata` |
| `dependencies` | `tuple[tuple[str, str], ...]` — include paths and digests |
| `fingerprint` | `str` — stable identity hash |

| Method | Returns |
| --- | --- |
| `render(inputs, validate=True)` | `str` — messages joined |
| `render_messages(inputs, validate=True)` | `list[Message]` |
| `validate_inputs(inputs)` | `dict[str, Any]` |
| `joined_template` | `str` — concatenated template source |
| `get_required_inputs()` / `get_optional_inputs()` | `list[str]` |
| `input_model()` / `output_model()` | `type[BaseModel] | None` |

`Prompt` is immutable.

## Running

```python
from promptkit import (
    run_prompt, run_prompt_async,
    run_prompt_text, run_prompt_text_async,
    run_structured, run_structured_async,
)
```

```python
run_prompt(prompt, inputs, engine, validate_inputs=True,
           cache=None, listeners=None, **options) -> Completion
```

`run_prompt_text` returns a plain `str`. `run_structured` returns
`ParsedCompletion[T]`, taking `output_model` and `max_parse_retries`.

Extra keyword arguments pass through to the engine (`temperature=`, `max_tokens=`,
`top_p=`, …).

## Types

```python
from promptkit import Completion, Message, Usage, Chunk, Capabilities, Role
```

### Completion

| Attribute | Meaning |
| --- | --- |
| `text` | The generated text |
| `model` | The model that answered |
| `usage` | `Usage` |
| `finish_reason` | Provider stop reason |
| `raw` | The provider's own response object |

`str(completion)` returns `.text` and `len(completion)` its length, so f-strings and
`print` behave as expected. `==` against a string does **not** — use `.text`.

### Usage

`prompt_tokens`, `completion_tokens`, `total_tokens`, and `estimated` — whether the
counts came from the provider or were guessed.

## Engines

```python
from promptkit import BaseEngine, OpenAIEngine, AnthropicEngine, OllamaEngine, CompatibleEngine
from promptkit import discover_engines, load_engine
```

| Method | |
| --- | --- |
| `complete(messages, **options)` | `Completion` |
| `acomplete(messages, **options)` | `Completion` |
| `stream(messages, **options)` | `Iterator[Chunk]` |
| `astream(messages, **options)` | `AsyncIterator[Chunk]` |
| `generate(prompt)` / `generate_async(prompt)` | `str` convenience |
| `cost_of(completion)` | `float | None` |
| `close()` / `aclose()` | Release the client |
| `client` | The underlying SDK client |
| `capabilities` | `Capabilities` |

Engines are sync and async context managers.

## Retry, cache, events

```python
from promptkit import RetryPolicy, Cache, MemoryCache, DiskCache, subscribe, unsubscribe
from promptkit.retry import NO_RETRY
from promptkit.events import listening, Recorder
```

## Linting and evaluation

```python
from promptkit import lint_prompt, Finding
from promptkit import EvalCase, EvalSuite, SuiteResult, run_suite
from promptkit.evals import load_suite, run_suite_async, register
```

## Errors

```python
from promptkit.errors import PromptKitError  # and the rest
```

See the [error reference](errors.md).

## Compatibility

From 1.0, PromptKit follows semantic versioning.

**Public API** is everything in `promptkit.__all__` plus documented YAML fields.
Anything else — modules under `promptkit.core`, private helpers, internal structure —
may change in a patch release.

Deprecations warn for one full minor release before removal.
