# Engines

An engine talks to a provider. PromptKit wraps the official SDKs rather than
reimplementing provider HTTP, so new parameters, response shapes, and error codes arrive
with an SDK upgrade instead of a PromptKit release.

## Installing

The base install has no HTTP client at all. Each provider is an extra:

| Engine | Extra | Wraps |
| --- | --- | --- |
| `OpenAIEngine` | `promptkit-core[openai]` | `openai` |
| `AnthropicEngine` | `promptkit-core[anthropic]` | `anthropic` |
| `OllamaEngine` | `promptkit-core[ollama]` | `ollama` |
| `CompatibleEngine` | `promptkit-core[openai]` | `openai` with a custom `base_url` |

Importing an engine module always works. Constructing one without its extra raises
`EngineNotFoundError` naming the exact install command.

```bash
promptkit engines
```

## Using one

```python
from promptkit.engines.openai import OpenAIEngine

with OpenAIEngine(api_key="sk-...", model="gpt-4o-mini") as engine:
    completion = engine.complete("Say hello")

print(completion.text, completion.usage)
```

Engines own their client for their lifetime. Use a context manager, or call `close()` /
`aclose()`. There is no `__del__` cleanup.

```python
async with AnthropicEngine() as engine:
    completion = await engine.acomplete("Say hello")
```

## Messages

`complete` takes a string or a list of `Message`:

```python
from promptkit.types import Message

engine.complete([
    Message(role="system", content="Be brief."),
    Message(role="user", content="Explain vector databases."),
])
```

`AnthropicEngine` hoists system messages into the Messages API's top-level `system`
parameter, because that is what it requires. You write the same thing either way.

## Capabilities

```python
OpenAIEngine.capabilities
# Capabilities(streaming=True, json_mode=True, system_role=True)
```

The runner reads these to degrade gracefully. An engine without `json_mode` gets a
schema instruction appended instead of a native structured-output request; an engine
without `system_role` gets system messages folded into the first user message.

## Streaming

```python
for chunk in engine.stream("Write a haiku"):
    print(chunk.text, end="", flush=True)
```

```bash
promptkit run haiku.yaml --stream
```

## OpenAI-compatible endpoints

One implementation covers everything that speaks the OpenAI wire format:

```python
from promptkit.engines.compatible import CompatibleEngine

CompatibleEngine(base_url="groq", model="llama-3.1-8b-instant")
CompatibleEngine(base_url="https://my-vllm.internal/v1", model="my-model")
```

Named shortcuts: `groq`, `together`, `openrouter`, `lmstudio`, `vllm`, `ollama`.

`CompatibleEngine` does not advertise `json_mode`, because compatible endpoints vary in
whether they implement it.

## Errors

Every provider exception is mapped onto one hierarchy, so this works the same across
providers:

```python
from promptkit.errors import RateLimitError, AuthenticationError

try:
    engine.complete("...")
except RateLimitError as e:
    wait(e.retry_after)
except AuthenticationError:
    ...
```

See the [error reference](../reference/errors.md).

## Dropping to the SDK

Anything outside PromptKit's scope is one attribute away:

```python
engine.client          # the underlying SDK client
completion.raw         # the provider's own response object
```

Use these for tool calling, assistants, batch APIs, or anything else PromptKit
deliberately does not model.

## Plugins

Engines resolve through the `promptkit.engines` entry-point group. Third-party engines
register the same way the built-ins do — see [writing an
engine](custom-engines.md).
