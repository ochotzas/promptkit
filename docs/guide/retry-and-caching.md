# Retry and caching

Three concrete options rather than a middleware pipeline. Each is the smallest thing
that serves its purpose.

## Retry

Retry is a constructor option on the engine, on by default.

```python
from promptkit.retry import RetryPolicy, NO_RETRY
from promptkit.engines.openai import OpenAIEngine

OpenAIEngine()                                       # 3 attempts, on by default
OpenAIEngine(retry=RetryPolicy(attempts=5))
OpenAIEngine(retry=NO_RETRY)                         # fail fast
```

```python
RetryPolicy(
    attempts=3,
    initial_backoff=0.5,
    max_backoff=30.0,
    multiplier=2.0,
    jitter=True,
)
```

Exponential backoff with full jitter, capped at `max_backoff`. A `Retry-After` header
overrides the computed delay.

**What is retried:** `RateLimitError` (429) and `ProviderError` with a 408, 409, 425,
or 5xx status, or no status at all (a connection failure).

**What is not:** authentication, bad requests, model-not-found, context-length. Retrying
those wastes time and money to get the same answer.

Provider SDK retries are disabled (`max_retries=0`), so there is exactly one retry layer
and one place to reason about it.

## Caching

Caching is an option on the runner, over a two-method protocol.

```python
from promptkit.cache import MemoryCache, DiskCache
from promptkit import run_prompt

cache = DiskCache(".promptkit-cache")
completion = run_prompt(prompt, inputs, engine, cache=cache)
```

`MemoryCache(max_entries=1024)` is process-local. `DiskCache(path)` survives restarts.

### The key

A cache entry is keyed on the prompt's **fingerprint**, the resolved inputs, the model,
and the sampling options. Editing a prompt or one of its partials changes the
fingerprint and therefore misses the cache — which is the behaviour you want.

**API keys never enter a cache key.** Any option named `api_key`, `key`,
`authorization`, `token`, or `secret` is stripped before hashing.

### Your own cache

```python
from promptkit.types import Completion

class RedisCache:
    def get(self, key: str) -> Completion | None: ...
    def set(self, key: str, completion: Completion) -> None: ...
```

Two methods. No registration, no plugin.

!!! warning "Caching hides variance"
    A cached run returns the same text forever. That is the point for cost control and
    the opposite of what you want while iterating on a prompt. Do not cache during
    evals.

## Why there is no middleware pipeline

A composable pipeline was considered and rejected. It is a framework you must learn
before you can set a timeout, and freezing its protocol at 1.0 would commit to an
abstraction no third party has pushed on yet.

Three explicit options are easier to document, easier to type, and easier to explain. If
real extension needs emerge that these cannot express, a pipeline can be added in a
later minor release — the reverse is not available.
