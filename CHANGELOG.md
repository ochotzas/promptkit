# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0]

The first stable release, and a complete rearchitecture of everything under the surface.
The public API is frozen and PromptKit now follows semantic versioning.

Upgrading from 0.1.x? **Your prompt files load unchanged** — that is asserted per-file by
the test suite. Read the [upgrade guide](docs/upgrading.md) and run
`python -m promptkit.codemod your_package/` for the mechanical parts.

### Added

**Prompts**

- **Message-based prompts.** `messages:` takes an ordered list with `system`, `user`, and
  `assistant` roles. The single `template:` form still works and is not deprecated.
- **Composition.** Share text between prompts with `{% include %}`, `{% extends %}`, and
  `{% import %}`, resolved by a loader confined to the prompt's directory. Directories
  prefixed with `_` hold partials.
- **`Prompt.fingerprint`** — a stable hash over messages, schemas, and resolved includes.
  Editing a shared partial changes the fingerprint of every dependent prompt, which is
  what makes caching correct. `version` is advisory metadata, not identity.
- **`PromptRegistry`** — loads a directory tree as dotted identifiers
  (`prompts/support/refund.yaml` becomes `support.refund`), cached with mtime
  invalidation.
- `version`, `metadata` (tags, author, model, temperature), `loads_prompt()`, and a
  published [JSON Schema](https://promptkit.ochotzas.com/schemas/prompt.schema.json) for
  prompt files so editors can validate and autocomplete them.

**Types and execution**

- **Real token usage.** `run_prompt` returns a `Completion` carrying text, model, usage,
  finish reason, and the raw provider response. Counts come from the provider;
  `Usage.estimated` says when a number was guessed, so a cost report cannot quietly lie.
- **Structured output.** `run_structured()` returns a validated `ParsedCompletion[T]`,
  using native JSON mode where the provider has it and re-prompting with the validation
  error where it does not.
- **Retry** as an engine constructor option — exponential backoff with jitter, honours
  `Retry-After`, retries 429 and 5xx but never 4xx, on by default.
- **Caching** as a `run_prompt` option over a two-method `Cache` protocol, with
  `MemoryCache` and `DiskCache`. API keys never enter a cache key.
- **Events** — `PromptRendered`, `RequestStarted`, `RequestCompleted`, `RequestFailed`,
  `ParseRetried` — with global, scoped, and per-call listeners. A listener that raises
  cannot break the run.
- **OpenTelemetry** behind `promptkit-core[otel]`, using `gen_ai.*` semantic conventions.
  No prompt or response content and no API keys are recorded unless explicitly opted in.

**Engines**

- **Provider SDKs behind extras** — `[openai]`, `[anthropic]`, `[ollama]`, `[all]`.
  Engines wrap the official SDKs rather than reimplementing provider HTTP.
- `AnthropicEngine` (system prompt hoisted to the top-level parameter, as the Messages
  API requires) and `CompatibleEngine` for any OpenAI-compatible endpoint, with
  shortcuts for Groq, Together, OpenRouter, vLLM and LM Studio.
- **Engine plugins.** Engines resolve through the `promptkit.engines` entry-point group;
  third-party engines register exactly as the built-ins do.
- **Streaming** on every engine, plus `promptkit run --stream`.
- One error hierarchy across providers, so `except RateLimitError` means the same thing
  everywhere. `Engine.client` and `Completion.raw` expose the SDK underneath.

**Quality tooling**

- **A linter** with nine rules and codes (PK001-PK009), three severities, `--strict`,
  `--format json`, and `--rules`.
- **An eval harness.** Suites live beside their prompt as `<name>.evals.yaml`.
  Assertions: `contains`, `not_contains`, `regex`, `equals`, `is_json`, `json_schema`,
  `max_latency`, `max_cost`, `max_tokens`, and an LLM `judge`. Concurrent, with terminal,
  JSON and JUnit XML output. `promptkit test` exits non-zero on regression.
- **Eval cassettes.** `promptkit test --record` captures provider responses once;
  every run after that replays them offline, free, and deterministically. Cassettes are
  keyed on the rendered messages and sampling options, so editing a prompt invalidates
  them and says exactly why. Commit the cassette and your evals run in CI with no API
  key.
- **A pytest plugin**, bundled — `pytest prompts/` collects every `*.evals.yaml` case as
  a test. With a cassette it runs offline in milliseconds; without one it skips with a
  reason rather than failing, so contributors without a key are not blocked.
- **`promptkit watch`** — re-lints prompts as you edit them, with no extra dependency.
  `--once` doubles as a CI lint gate.
- **Registry version pinning.** `registry.get("support.refund@2.1.0")`,
  `@latest`, and `versions()`. Versions sort numerically, so `2.10.0` beats `2.1.0`.
- **A pricing snapshot** covering 328 models across OpenAI, Anthropic, Groq, Mistral,
  xAI, DeepSeek, Together and Ollama, vendored at `promptkit/data/pricing.json` with a
  refresh script and a weekly workflow that opens a pull request when rates move.
- **New CLI commands:** `test`, `diff`, `list`, `init`, `engines`, plus `cost --models`
  and `render --messages`. Shell completion is enabled.
- **`python -m promptkit.codemod`** for the 0.1.x upgrade. Dry run by default, prints a
  unified diff, and only rewrites what it can do unambiguously.
- **A documentation site** at [promptkit.ochotzas.com](https://promptkit.ochotzas.com/).
- `py.typed`, so the type hints reach consumers. Exact token counts behind `[tokens]`.

### Changed

- **Variables are no longer limited to `name` and `context`.** Use repeatable
  `--set key=value`, `--vars` with JSON, or `--vars-file`. `--set` coerces to the type
  your schema declares.
- **Templates render in a Jinja sandbox**, and includes resolve through a confined
  loader that refuses absolute paths, `..` traversal, and symlinks escaping the root.
  Rendering a prompt file you did not write is safe.
- **The type-string language is frozen** at `str`, `int`, `float`, `bool`, `list`,
  `dict`, and `X | None`. Anything richer uses JSON Schema or a Pydantic model.
- Sync and async engine paths share one pure layer, so they cannot drift.
- The base install has **no HTTP client and no provider SDK**. Loading, rendering,
  validation, composition, linting and cost estimation need nothing network-shaped.
- Tests moved out of the shipped package; `promptkit/tests/` no longer installs into
  site-packages.
- ruff replaces black and isort; mypy runs `strict`. CI covers Python 3.10-3.13 on
  Linux, macOS and Windows, with a lowest-supported-dependency job.
- PyPI publishing uses Trusted Publishing with build provenance instead of a token.
- `promptkit test` builds its engine lazily, so a run served entirely from a cassette
  never needs credentials.
- Dropped the unused `pytest-asyncio` dev dependency; async tests use `asyncio.run`.

### Fixed

- **Model pricing could be confidently wrong.** Lookup resolved an unknown model to its
  longest matching prefix, so `claude-opus-4-5` was priced as `claude-opus-4` — three
  times too expensive. A name now resolves only as an exact entry, a dated snapshot of
  one, or an override; anything else reports no cost at all.
- **`pyyaml>=6.0` could not build** on Python 3.12+, and `create_schema_model` did not
  work on the declared minimum Pydantic. Both floors were wrong and are now tested.
- **Validation was ~40x slower than it needed to be** — schema models were rebuilt on
  every call. A simple render went from ~98µs to ~7µs.
- **Registry loads re-globbed the tree on every lookup.** A warm load of 100 prompts went
  from ~103ms to ~0.15ms.
- The sync and async OpenAI paths had drifted; `render` collected inputs twice; engines
  cleaned up in `__del__`; `setup.py` declared a different distribution name and four
  dependencies the code never imported.

### Removed

- `setup.py` — `pyproject.toml` is authoritative.
- `Prompt.template` — use `Prompt.messages` or `joined_template`. The `template=`
  argument and the `template:` YAML key remain.
- `promptkit.utils.tokens.get_model_pricing` — use `promptkit.pricing.get_pricing`.
- The CLI's `--name` and `--context` flags — use `--set key=value`.
- The engine implement-either fallback. A custom engine implements `_complete` returning
  a `Completion`; `generate` remains as a convenience.

### Breaking

- `run_prompt` returns a `Completion`, not a `str`. It stringifies to its text, so
  f-strings and `print` are unaffected, but `==` against a string is not. Use `.text`, or
  `run_prompt_text`.
- `pydantic.ValidationError` is now `InputValidationError`. Pydantic's exception cannot
  be subclassed alongside our base class, so this one has no compatibility shim; it does
  subclass `ValueError` and forwards `.errors()`.
- Provider SDKs must be installed as an extra.
- `OllamaEngine(base_url=...)` is now `OllamaEngine(host=...)`.

### Version numbering

The published history goes 0.1.1 → 1.0.0. Versions 0.2.0 through 0.6.0 were internal
development milestones during the rearchitecture and were never released to PyPI; they
are recorded as phases in [MIGRATION.md](MIGRATION.md) rather than as releases here.

### Compatibility

From 1.0, the public API is everything exported from `promptkit.__all__` plus documented
YAML fields. Anything else is internal and may change in a patch release. Deprecations
warn for one full minor release before removal.

## [0.1.1] - 2026-01-27

### Changed
- Simplified and cleaned up all docstrings
- Rewrote documentation to match actual implementation
- Removed references to non-existent features

### Fixed
- Documentation now accurately reflects the API
- Removed non-existent `prompt_dir` parameter from examples
- Fixed CLI command documentation

## [0.1.0] - 2025-06-28

### Added
- YAML-based prompt definitions with Jinja2 templating
- Input validation using Pydantic schemas
- OpenAI engine with sync/async support
- Ollama engine for local models
- Token estimation and cost calculation
- CLI commands: `run`, `render`, `lint`, `info`, `cost`
- Example prompts and usage scripts

### Features
- `Prompt` class for structured prompt management
- `load_prompt()` and `save_prompt()` for YAML files
- `run_prompt()` and `run_prompt_async()` for execution
- Extensible `BaseEngine` architecture

### Technical
- Python 3.10+ required
- Full type hints
- Pydantic v2 for validation
- httpx for HTTP requests
