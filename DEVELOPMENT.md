# Development

Internals and workflow for people working on PromptKit itself. For contribution rules,
see [CONTRIBUTING.md](CONTRIBUTING.md).

## Requirements

Python 3.10 or newer. CI runs 3.11 and 3.12 today, expanding to 3.10 through 3.13 in
migration phase 2.

## Commands

| Command | What it does |
| --- | --- |
| `make install-dev` | Editable install with dev extras, installs pre-commit hooks |
| `make test` | Run the test suite |
| `make test-cov` | Tests with an HTML and terminal coverage report |
| `make lint` | `ruff check` and `ruff format --check` |
| `make format` | `ruff check --fix` and `ruff format` |
| `make type-check` | mypy over `promptkit/`, `tests/` and `scripts/` |
| `make all` | format, lint, type-check, test |
| `make bench` | Run the benchmarks |
| `make build` | Build sdist and wheel |
| `make docs` | Build the MkDocs site with `--strict` |
| `make serve-docs` | Serve the docs with live reload |
| `make pricing-refresh` | Update the vendored model pricing snapshot |
| `make pricing-check` | Fail if the pricing snapshot is out of date |
| `make lock` | Refresh `uv.lock` |
| `make codemod` | Preview the 1.0 codemod (`TARGET=path`) |
| `make check-deps` | Report which dev tools are installed |

black and isort are gone — ruff does both. Do not reintroduce them.

## Layout

```
promptkit/
├── errors.py       exception hierarchy — everything public raises from here
├── types.py        Message, Usage, Completion, Chunk, Capabilities
├── events.py       lifecycle events and listener registration
├── cache.py        Cache protocol, MemoryCache, DiskCache
├── retry.py        RetryPolicy and retryability rules
├── pricing.py      rate lookup over the vendored snapshot
├── codemod.py      0.1.x to 1.0 upgrade tool
├── core/           Prompt, messages, loader, sandbox, schemas, registry, lint, runner
├── engines/        BaseEngine, provider engines over official SDKs, plugin registry
├── evals/          cases, assertions, concurrent runner, reporters
├── telemetry/      OpenTelemetry listener (otel extra)
├── data/           generated pricing snapshot — never edit by hand
├── schemas/        published JSON Schema for prompt files
├── utils/          token counting, logging
└── cli/            Typer app; one module per command under cli/commands/
benchmarks/         pytest-benchmark suites, run in CI
docs/               MkDocs Material, deployed to promptkit.ochotzas.com
scripts/            maintenance scripts (pricing refresh)
tests/              outside the package, not shipped in the wheel
```

## Things worth knowing

**The Jinja environment uses `StrictUndefined`.** An unprovided template variable is an
error, never an empty string. This is load-bearing: silent empty interpolation into a
prompt is the exact class of bug PromptKit exists to prevent.

**`Prompt` is frozen.** Rendering is a pure function of the prompt and its inputs.
A single module-level `PromptCompiler` (`core/compiler.py:default_compiler`) is shared
across all prompts.

**Pricing comes from a generated snapshot** at `promptkit/data/pricing.json` — run
`make pricing-refresh`, never edit it by hand. Lookup resolves exactly three ways: an
exact key, a dated or `-latest` snapshot of a key, or a registered override. There is
deliberately **no prefix matching** — it once priced `claude-opus-4-5` as
`claude-opus-4`, three times too high. An unknown model must return `None`.

**Engines do not construct themselves.** The runner never builds an engine; callers pass
one in. Only the CLI maps engine names to classes.

## Testing

```bash
make test
pytest tests/test_prompt.py::TestPrompt -v
pytest tests/ -k pricing
```

**Tests cannot make network calls.** `tests/conftest.py` blocks outbound `connect` and
`getaddrinfo` outside localhost, and `tests/test_no_network.py` verifies the guard
itself. Engine tests exercise the pure request-building and response-parsing helpers
directly; transport tests inject a `MockTransport` through the SDK's own `http_client`.

Note that the OpenAI and Anthropic SDKs use `httpx2` on recent versions and `httpx` on
older ones, so tests resolve the stack from the SDK rather than assuming. `respx` does
not work here.

## Releasing

1. Update `__version__` in `promptkit/__init__.py` — the only place it lives.
2. Move `CHANGELOG.md` entries from `## [Unreleased]` into a dated version section.
3. Merge `dev` into `main`.
4. Publish a GitHub release; the CD workflow builds and uploads to PyPI.
