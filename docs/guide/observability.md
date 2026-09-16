# Events and observability

Every prompt run emits typed lifecycle events. Listeners observe; they cannot alter a
request.

## Events

| Event | When | Carries |
| --- | --- | --- |
| `PromptRendered` | After rendering, before any call | `characters`, `message_count` |
| `RequestStarted` | Before the provider call | `engine`, `attempt` |
| `RequestCompleted` | On success or a cache hit | `usage`, `duration_seconds`, `cost`, `cached` |
| `RequestFailed` | On any failure | `error`, `error_type`, `duration_seconds` |
| `ParseRetried` | Structured output failed to parse | `attempt`, `error` |

Every event carries `prompt_name` and `model`.

## Listening

```python
from promptkit.events import subscribe, RequestCompleted

def log_cost(event):
    if isinstance(event, RequestCompleted):
        print(f"{event.prompt_name}: {event.usage.total_tokens} tokens, ${event.cost}")

subscribe(log_cost)
```

Scoped to a block:

```python
from promptkit.events import listening, Recorder

recorder = Recorder()

with listening(recorder):
    run_prompt(prompt, inputs, engine)

recorder.of(RequestCompleted)[0].cost
```

Scoped to a single call:

```python
run_prompt(prompt, inputs, engine, listeners=[recorder])
```

A listener that raises cannot break the run — exceptions from listeners are swallowed by
design. Observation must never be able to take down the thing being observed.

## OpenTelemetry

```bash
pip install 'promptkit-core[otel]'
```

```python
from promptkit.telemetry import install

install()
```

Each run becomes a `promptkit.run` span with OpenTelemetry's `gen_ai.*` semantic
conventions:

| Attribute | Value |
| --- | --- |
| `gen_ai.request.model` | The model that answered |
| `gen_ai.usage.input_tokens` | Prompt tokens |
| `gen_ai.usage.output_tokens` | Completion tokens |
| `promptkit.prompt.name` | Prompt name |
| `promptkit.cost_usd` | Cost, when pricing is known |
| `promptkit.usage.estimated` | Whether counts were measured or estimated |
| `promptkit.cached` | Whether the response came from cache |
| `promptkit.duration_seconds` | Wall time |

Failures set the span status to error and record `promptkit.error.type`.

**No prompt or response content is recorded**, and neither are API keys. Error messages
are only attached when you opt in:

```python
install(include_content=True)
```

Opt in deliberately: prompt and error text can contain whatever your users typed.

## Writing your own listener

`OpenTelemetryListener` is the worked example — about forty lines in
`promptkit/telemetry/otel.py`. A listener is any callable taking one event:

```python
def to_statsd(event):
    if isinstance(event, RequestCompleted):
        statsd.timing("llm.duration", event.duration_seconds * 1000)
        statsd.increment("llm.tokens", event.usage.total_tokens)

subscribe(to_statsd)
```

## Logging

PromptKit logs through the standard library under the `promptkit` logger hierarchy and
attaches no handlers of its own, so it inherits your application's configuration.

```python
import logging

logging.getLogger("promptkit").setLevel(logging.DEBUG)
```
