# Writing an engine

An engine is a class with one required method. Third-party engines are first-class — the
built-ins register through the same entry-point group.

## The minimum

```python
from typing import Any, ClassVar

from promptkit.engines.base import BaseEngine
from promptkit.types import Capabilities, Completion, Message, Usage


class MyEngine(BaseEngine):
    capabilities: ClassVar[Capabilities] = Capabilities(
        streaming=False, json_mode=False, system_role=True
    )

    def __init__(self, model: str = "my-model", **kwargs: Any) -> None:
        super().__init__(model)
        self.client = MyProviderClient(**kwargs)

    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        raw = self.client.generate(
            [{"role": m.role, "text": m.content} for m in messages]
        )

        return Completion(
            text=raw.output,
            model=self.model,
            usage=Usage(raw.tokens_in, raw.tokens_out),
            finish_reason=raw.stop,
            raw=raw,
        )
```

That is enough. `complete`, `acomplete`, `generate`, retry, cost, and lifecycle are all
provided by the base class.

## Sans-I/O: the pattern that matters

Put request building, response parsing, and error mapping in **module-level pure
functions**, and keep the transport methods thin:

```python
def build_params(messages, model, temperature=None, **extra):
    ...

def parse_response(raw, model) -> Completion:
    ...

def map_error(error: Exception, model: str) -> EngineError:
    ...


class MyEngine(BaseEngine):
    def _complete(self, messages, **options):
        try:
            raw = self.client.generate(**build_params(messages, self.model, **options))
        except Exception as e:
            raise map_error(e, self.model) from e

        return parse_response(raw, self.model)

    async def _acomplete(self, messages, **options):
        try:
            raw = await self.aclient.generate(
                **build_params(messages, self.model, **options)
            )
        except Exception as e:
            raise map_error(e, self.model) from e

        return parse_response(raw, self.model)
```

Two benefits, and both are real:

- **Sync and async cannot drift.** Everything except the call itself is shared.
- **The pure layer tests with no network and no mocking.** Pass a dict to
  `parse_response` and assert on the `Completion`.

Do **not** implement sync by driving an event loop from async. It fails inside any
caller that already has one running — a notebook, a web handler, an async test.

## Async

`_acomplete` defaults to calling `_complete`. Override it when your provider has a real
async client.

## Errors

Map provider exceptions onto PromptKit's hierarchy so `except RateLimitError` means the
same thing everywhere:

```python
from promptkit.errors import (
    AuthenticationError, ContextLengthError, EngineError,
    ModelNotFoundError, ProviderError, RateLimitError,
)

def map_error(error: Exception, model: str) -> EngineError:
    if isinstance(error, MyAuthError):
        return AuthenticationError(str(error), model=model)

    if isinstance(error, MyThrottled):
        return RateLimitError(str(error), model=model, retry_after=error.retry_after)

    if isinstance(error, MyProviderError):
        return ProviderError(str(error), model=model, status_code=error.status)

    raise error
```

Re-raise anything you do not recognise. Swallowing an unexpected exception into
`ProviderError` hides bugs.

Returning `RateLimitError` or a 5xx `ProviderError` is what makes the built-in retry
engage — the mapping is the retry policy.

## Capabilities

```python
capabilities = Capabilities(streaming=True, json_mode=True, system_role=False)
```

- `json_mode` — the provider has native structured output. The runner sends the schema
  as an option named `json_schema`; without it, a schema instruction is appended.
- `system_role` — the provider accepts system messages. Without it, system content is
  folded into the first user message.
- `streaming` — `stream` and `astream` are implemented.

Declare honestly. A false `json_mode` produces confusing failures.

## Lifecycle

```python
    def close(self) -> None:
        self._client = None

    async def aclose(self) -> None:
        self.close()
        await self._aclient.close()
```

Context manager support comes from the base class. Never clean up in `__del__`.

## Streaming

```python
    def stream(self, messages, **options):
        for raw in self.client.stream(**build_params(...)):
            yield Chunk(text=raw.delta, raw=raw)
```

## Registering as a plugin

In your package's `pyproject.toml`:

```toml
[project.entry-points."promptkit.engines"]
myprovider = "mypackage.engine:MyEngine"
```

Then it appears in `promptkit engines` and works with `--engine myprovider`. No PR to
PromptKit required.

## Testing

Test the pure functions directly:

```python
def test_usage_is_read_from_the_response():
    raw = SimpleNamespace(output="hi", tokens_in=11, tokens_out=4, stop="done")

    assert parse_response(raw, "m").usage == Usage(11, 4)
```

For transport, inject a mock HTTP client rather than patching globally — the SDK you
wrap may not use the HTTP library your mocking tool patches. PromptKit's own suite
blocks outbound connections entirely to make accidental network calls impossible.
