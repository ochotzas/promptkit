# Architecture

This document describes the target architecture for PromptKit 1.0. For the staged path
from the current 0.1.x codebase to this design, see [MIGRATION.md](MIGRATION.md).

## Design principles

1. **Prompts are data, not code.** A prompt is a declarative, versioned, reviewable
   artifact. Nothing in a prompt file executes arbitrary Python.
2. **Sans-I/O core, two real transports.** Request construction, response parsing, and
   error mapping are pure functions shared by a synchronous and an asynchronous client.
   Neither is derived from the other, so the sync path never has to drive an event loop.
3. **Provider churn is someone else's problem.** Engines wrap official provider SDKs
   installed as extras, rather than reimplementing provider HTTP.
4. **Typed edges.** Inputs are validated before rendering, outputs are validated after
   generation. Both failures are PromptKit exceptions, never leaked third-party ones.
5. **Providers are plugins.** A third party can ship an engine in their own package and
   have PromptKit discover it, without a PR to this repository.
6. **No hidden network calls.** The core renders and validates; only an engine talks to
   a provider, and only when the caller hands one over.
7. **Untrusted templates are safe to render.** Prompt files may come from a shared
   registry, a PR, or an end user.
8. **Borrow types, do not invent them.** Where Pydantic or JSON Schema already express
   something, PromptKit defers to them instead of growing its own type language.

## Scope

PromptKit manages prompts: authoring, validating, versioning, rendering, executing, and
testing them. It is deliberately **not** an agent framework.

Out of scope, permanently:

| Not provided | Use instead |
| --- | --- |
| Tool / function calling | The provider SDK directly, or an agent framework |
| Agent loops, planning, multi-step orchestration | LangGraph, the Agents SDKs |
| Conversation state and memory across turns | Your application, or a framework |
| Vector stores, retrieval, RAG pipelines | A dedicated retrieval library |
| Fine-tuning and training | Provider tooling |

An engine exposes `raw` on every `Completion` and its underlying SDK client as
`.client`, so dropping down to the provider for anything on that list is one attribute
access away rather than a fork.

## Package layout

```
promptkit/
├── __init__.py            public API surface, re-exports only
├── py.typed               PEP 561 marker
├── errors.py              exception hierarchy
├── types.py               Role, Message, Usage, Completion, Chunk
├── pricing.py             per-model rates with a user override hook
├── cache.py               content-addressed response cache
├── events.py              typed lifecycle events and listener registration
├── core/
│   ├── prompt.py          Prompt model
│   ├── message.py         message template list and rendering
│   ├── schema.py          type-string and JSON Schema to Pydantic model
│   ├── template.py        sandboxed Jinja environment and confined loader
│   ├── loader.py          YAML to Prompt, Prompt to YAML
│   ├── registry.py        directory-backed, namespaced prompt registry
│   └── runner.py          execution: render, call, parse, retry
├── engines/
│   ├── base.py            Engine ABC, Capabilities
│   ├── plugins.py         entry-point discovery and name resolution
│   ├── openai.py          sync + async over the openai SDK
│   ├── anthropic.py       sync + async over the anthropic SDK
│   ├── ollama.py          sync + async over the ollama SDK
│   └── compatible.py      any OpenAI-compatible base_url
├── telemetry/
│   └── otel.py            OpenTelemetry listener (optional extra)
├── evals/
│   ├── case.py            EvalCase model
│   ├── assertions.py      contains, not_contains, regex, json_schema, judge
│   ├── runner.py          concurrent execution over a suite
│   └── report.py          terminal, JSON, and JUnit XML reporters
├── utils/
│   ├── tokens.py          estimation, exact counts via optional tiktoken
│   └── logging.py
└── cli/
    ├── main.py            Typer app assembly only
    └── commands/          one module per command
tests/                     outside the distributed package
```

Every directory is a real package with an `__init__.py`. Tests are not shipped.

## Core abstractions

### Prompt

```
Prompt
  name: str
  version: str
  description: str
  messages: list[MessageTemplate]
  input_schema: dict[str, str] | JsonSchema | None
  output_schema: JsonSchema | None
  metadata: PromptMetadata
```

A `MessageTemplate` is a `role` (`system`, `user`, `assistant`) plus a Jinja template
string. The 0.1.x single `template:` key is loaded as one `user` message, so existing
YAML files keep working.

`metadata` carries non-executable context: tags, author, recommended model, temperature
hint, and a free-form `extra` mapping. Nothing in metadata changes rendering behaviour.

`Prompt` is immutable after construction. Rendering is a pure function of the prompt and
its inputs. `Prompt.fingerprint` is a stable hash over messages and schema; the response
cache and the eval harness both key on it, and it is the honest identity of a prompt.
The `version` field is advisory metadata for humans, not an identity — it is not
enforced against content.

### Schemas

There are two ways to describe inputs, and they exist for different audiences.

**Type strings** stay exactly as they are today — `str`, `int`, `float`, `bool`, `list`,
`dict`, and `X | None`. They are terse and readable for the common case, and that is the
whole of their job. They will not grow parameterised generics, constrained forms, or
enums. Any type-string PromptKit cannot parse raises `SchemaError` naming the field.

**JSON Schema** covers everything else. `input_schema` accepts a JSON Schema object
instead of a type-string mapping, and `output_schema` accepts only JSON Schema. Both
compile to a Pydantic model internally.

From Python, callers bypass both and pass a Pydantic model directly:

```
run_prompt(prompt, inputs, engine, output_model=Invoice)
```

This is the recommended path for typed applications; the type checker infers the parsed
result, which no string-based schema can offer.

The rule behind this split: PromptKit owns a small readable shorthand, and delegates
real type expression to Pydantic and JSON Schema rather than growing a third type
language nobody asked for.

### Rendering and composition

`template.py` owns a single `SandboxedEnvironment` with `StrictUndefined`,
`trim_blocks`, and `lstrip_blocks`. The sandbox blocks attribute access to dunders and
unsafe callables, which makes it safe to render a prompt file you did not write. A
compiled-template cache lives at module level, keyed by template hash, so compilation
happens once per unique template process-wide rather than once per `Prompt` instance.

Prompts compose through Jinja's own mechanisms — `{% include %}`, `{% extends %}`, and
`{% import %}` — backed by a **confined loader** rooted at the registry directory:

```
prompts/
├── _partials/
│   ├── tone.j2
│   └── safety.j2
└── support/
    └── refund.yaml        {% include "_partials/tone.j2" %}
```

The loader resolves every path relative to the registry root, rejects absolute paths and
any path escaping the root after normalisation, and refuses symlinks that point outside
it. Directories prefixed with `_` hold partials and are not themselves loaded as
prompts.

Composition is why the sandbox is not optional: the moment one prompt file can pull in
another, template content and template *source* become separate trust domains.

`Prompt.fingerprint` covers resolved includes, so editing a shared partial correctly
invalidates the cache of every prompt that uses it.

### Completion

Engines return a `Completion`, not a string:

```
Completion
  text: str
  model: str
  usage: Usage            prompt_tokens, completion_tokens, total_tokens
  finish_reason: str | None
  raw: Any                the provider SDK's own response object
```

This is what makes cost reporting real rather than estimated: `usage` comes from the
provider response. Estimation remains available for pre-flight `promptkit cost`, which
is by definition a guess.

`Completion` defines `__str__` returning `text`, so code that interpolates a result into
a string keeps working.

### Engine

```
Engine (ABC)
  model: str
  capabilities: Capabilities      streaming, json_mode, system_role
  client                          the underlying provider SDK client

  complete(messages, **options) -> Completion            [abstract]
  async acomplete(messages, **options) -> Completion     [abstract]
  stream(messages, **options) -> Iterator[Chunk]
  async astream(messages, **options) -> AsyncIterator[Chunk]
  close() / aclose()
```

Both `complete` and `acomplete` are abstract and each is a real implementation. What
prevents them from drifting apart — the drift that already exists in today's
`engines/openai.py`, where the sync path handles `KeyError` and the async path does not
— is that everything except the call itself is a pure function they share:

```
build_params(messages, options, capabilities) -> dict
parse_response(raw) -> Completion
map_error(exc) -> EngineError
```

Each transport method is then roughly ten lines: build, call, parse, with error mapping
in an `except` clause. The pure functions are unit-tested without any transport at all,
which is where the real coverage lives.

This is the same structure httpx, urllib3, and the OpenAI and Anthropic SDKs use, and it
is chosen over deriving sync from async deliberately. Running a coroutine on a private
event loop from a synchronous method fails inside any caller that already has a loop
running — a notebook, a FastAPI handler, an async test — and burning a worker thread to
dodge that is a real cost paid on every call.

`Capabilities` lets the runner degrade gracefully: an engine without `system_role`
support gets the system message folded into the first user message rather than an error.

Engines own their SDK client for their lifetime, expose `close()` and `aclose()`, and
support both context manager protocols. Cleanup never happens in `__del__`.

### Engines and provider SDKs

Engines wrap the official provider SDKs, each behind an extra:

| Engine | Extra | Wraps |
| --- | --- | --- |
| `OpenAIEngine` | `promptkit[openai]` | `openai` |
| `AnthropicEngine` | `promptkit[anthropic]` | `anthropic` |
| `OllamaEngine` | `promptkit[ollama]` | `ollama` |
| `CompatibleEngine` | `promptkit[openai]` | `openai` with a custom `base_url` |

The base install pulls in no provider dependency at all. Importing an engine without its
extra raises `EngineNotFoundError` naming the exact `pip install` command.

The alternative — raw `httpx` against each provider's REST API — was the original plan
and is rejected. It means personally tracking new sampling parameters, response shape
changes, streaming event formats, prompt-caching headers, and error-code changes across
every provider, forever, for the part of PromptKit least differentiated from what the
SDKs already do. That maintenance budget is better spent on prompts as versioned,
lintable, testable data, which is the part nothing else does well.

`CompatibleEngine` covers Groq, Together, vLLM, LM Studio, and OpenRouter with one
implementation, since all of them speak the OpenAI wire format.

### Engine plugins

Engines resolve by name through the `promptkit.engines` entry-point group. The built-in
providers register themselves the same way any third-party package would, so there is no
privileged path. `promptkit engines list` shows what is installed.

### Reliability and observability

There is no middleware pipeline. Retry, caching, and observability are three concrete
needs, and each gets the smallest thing that serves it.

**Retry** is a constructor option on every engine, implemented once in the base class
around the transport call: `Engine(retry=RetryPolicy(attempts=3))`, with exponential
backoff, jitter, and `Retry-After` honoured. It defaults to on. Provider SDKs have their
own retry behaviour, which PromptKit disables so there is exactly one retry layer and
one place to reason about it.

**Caching** is a runner option: `run_prompt(..., cache=DiskCache(path))`. The key is the
prompt fingerprint, the resolved inputs, the model, and the sampling options; API keys
never enter it. `Cache` is a two-method protocol (`get`, `set`), so a Redis or in-memory
implementation is a small class, not a plugin.

**Observability** is a listener API over typed lifecycle events — `PromptRendered`,
`RequestStarted`, `RequestCompleted`, `RequestFailed`, `ParseRetried` — each carrying
prompt name, version, fingerprint, model, usage, and duration. Listeners register
globally or per runner and cannot alter the request, which is the point: observation is
not interception. The OpenTelemetry integration is one listener shipped behind an extra,
and it is the worked example for anyone writing their own.

A composable pipeline was considered and rejected. It is a framework users must learn
before they can set a timeout, and freezing its protocol at 1.0 commits to an
abstraction no third party has yet pushed on. Three explicit options are easier to
document, easier to type, and easier to explain. If real extension needs emerge that
these cannot express, a pipeline can be added in 1.1 — the reverse is not available.

### Structured output

When a prompt declares `output_schema`, or a caller passes `output_model`, the runner:

1. Compiles the schema to a Pydantic model.
2. Uses the provider's native structured-output mode when `capabilities.json_mode` is
   set, and otherwise appends a schema instruction to the final message.
3. Validates the response, and on failure re-prompts with the validation error attached,
   up to `max_parse_retries`.
4. Returns a `ParsedCompletion[T]` carrying both the model instance and the raw
   `Completion`.

### Registry

A registry maps a directory tree to namespaced prompt identifiers: `prompts/support/
refund.yaml` becomes `support.refund`. It resolves versions, caches parsed prompts with
mtime invalidation, roots the confined template loader, and is the unit the CLI and eval
harness operate on.

### Evaluation

An eval suite lives next to its prompt as `<prompt>.evals.yaml`: a list of cases, each
with inputs and assertions. Assertions are pure predicates over a `Completion` except
for `judge`, which calls an engine. `promptkit test` runs a suite concurrently and can
emit JUnit XML, so prompt regressions fail CI like any other test.

## Error hierarchy

```
PromptKitError
├── PromptError
│   ├── PromptNotFoundError
│   ├── PromptParseError          malformed YAML or missing fields
│   ├── TemplateError             compilation, rendering, or include resolution
│   └── SchemaError               unsupported type string or invalid JSON Schema
├── ValidationError               wraps pydantic, keeps .errors()
│   ├── InputValidationError
│   └── OutputValidationError
├── EngineError
│   ├── EngineNotFoundError       unknown name, or extra not installed
│   ├── AuthenticationError
│   ├── RateLimitError            carries retry_after
│   ├── ModelNotFoundError
│   ├── ContextLengthError
│   └── ProviderError             everything else, keeps status and body
└── EvalError
```

Every exception carries structured attributes, not just a message string. Each engine's
`map_error` translates provider SDK exceptions onto this hierarchy, so
`except RateLimitError` works identically across OpenAI, Anthropic, and Ollama.

## Configuration

Precedence, highest first: explicit arguments, environment variables, a
`[tool.promptkit]` table in the consuming project's `pyproject.toml`, then defaults.
API keys are read from the environment only, never from a file PromptKit parses, and
are never included in log output, exception messages, telemetry attributes, or cache
keys.

## Dependency policy

The base install stays small: `pydantic`, `jinja2`, `pyyaml`, `typer`, `rich`.
Everything else is an extra — one per provider, `tiktoken` for exact token counts,
`otel` for OpenTelemetry, and `promptkit[all]` for the lot.

Provider SDKs are extras rather than core dependencies, which keeps the base install
lean without paying the cost of reimplementing provider HTTP. A user who installs
`promptkit` alone gets prompt loading, rendering, validation, linting, and diffing with
no network dependency in the tree.

## Compatibility contract

From 1.0, PromptKit follows semantic versioning. The public API is what
`promptkit.__all__` exports plus documented YAML fields. Anything else is internal and
may change in a patch release. Deprecations warn for one minor release before removal.
