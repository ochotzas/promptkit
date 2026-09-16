# PromptKit

Python library for structured LLM prompt engineering. Prompts are declared in YAML
(Jinja2 template + typed input schema), validated with Pydantic, and executed through
a pluggable engine abstraction. Ships a Typer/Rich CLI.

Distribution name is `promptkit-core`; import name is `promptkit`.
License MIT. Public community project — treat every public symbol as a contract.

**PromptKit is at 1.0. The public API is frozen and semver applies.** Anything in
`promptkit.__all__` plus documented YAML fields is a contract; removing or changing it
needs a deprecation that warns for a full minor release first. Everything else is
internal.

[ARCHITECTURE.md](ARCHITECTURE.md) is the design. [MIGRATION.md](MIGRATION.md) records
how it was reached and what was deliberately deferred — read it before proposing
something that was already considered and rejected (a middleware pipeline, a richer
type-string language, tool calling).

## Layout

| Path | Role |
| --- | --- |
| `promptkit/errors.py` | Exception hierarchy — everything public raises from here |
| `promptkit/types.py` | `Message`, `Usage`, `Completion`, `Chunk`, `Capabilities` |
| `promptkit/events.py` | Lifecycle events and listener registration |
| `promptkit/cache.py` | `Cache` protocol, `MemoryCache`, `DiskCache`, key derivation |
| `promptkit/retry.py` | `RetryPolicy` and retryability rules |
| `promptkit/pricing.py` | Rate lookup over the vendored snapshot in `promptkit/data/` |
| `promptkit/core/` | `Prompt`, messages, YAML loader, sandboxed compiler, schemas, runner |
| `promptkit/core/template.py` | Confined Jinja loader and include-dependency resolution |
| `promptkit/core/jsonschema.py` | JSON Schema to Pydantic compilation |
| `promptkit/schemas/` | Published JSON Schema for prompt files |
| `promptkit/engines/` | `BaseEngine`, provider engines over official SDKs, plugin registry |
| `promptkit/core/structured.py` | JSON extraction, output validation, repair loop |
| `promptkit/utils/` | Token estimation, pricing tables, logging |
| `promptkit/cli/` | Typer app; one module per command under `cli/commands/` |
| `promptkit/evals/` | Eval cases, assertions, runner, reporters, cassettes |
| `promptkit/pytest_plugin.py` | pytest11 plugin collecting `*.evals.yaml` |
| `promptkit/core/registry.py` | Directory-backed, namespaced prompt registry |
| `promptkit/core/lint.py` | Lint rules PK001-PK009 |
| `examples/` | Runnable YAML prompts and a demo script |
| `docs/` | MkDocs Material, deployed to https://promptkit-core.ochotzas.com/ |
| `benchmarks/` | pytest-benchmark suites, run in CI |
| `promptkit/telemetry/` | OpenTelemetry listener behind the `otel` extra |
| `promptkit/codemod.py` | 0.1.x to 1.0 upgrade tool |
| `tests/` | Test suite, top-level and not shipped in the wheel |

## Commands

```
make install-dev     # editable install with dev extras + pre-commit hooks
make test            # pytest
make test-cov        # pytest with coverage, fails under COVERAGE_FLOOR (80)
make lint            # ruff check + ruff format --check
make format          # ruff check --fix + ruff format
make type-check      # mypy (strict = true)
make lock            # refresh uv.lock
make all             # format, lint, type-check, test
make docs            # build the MkDocs site (strict)
make serve-docs      # live-reload docs
make bench           # run benchmarks
```

## Code style

- **No comments. No docstrings.** Names and types carry the meaning. This applies to
  all new and modified code without exception. Do not reintroduce them when editing a
  file that still has them.
- Full type annotations on every function and method; mypy runs with
  `disallow_untyped_defs` and `disallow_incomplete_defs`.
- ruff for linting and formatting, line length 88. black and isort are gone — do not
  reintroduce them. Lint config lives in `[tool.ruff.lint]` in `pyproject.toml`; prefer
  a targeted `per-file-ignores` entry over a `# noqa` comment, since comments are banned.
- Python 3.10+ syntax is available (`X | None`, `list[str]`), but the codebase still
  mixes `typing.Optional` and `|`. Prefer the modern form in new code.
- Pydantic v2 only (`model_config`, `model_dump`, `model_post_init`).
- Errors raised out of the library must be types from `promptkit/errors.py`, never bare
  `ValueError` or third-party exceptions leaking from dependencies. Add to the hierarchy
  rather than raising something generic.
- Typer command help lives in `@app.command(help=..., epilog=...)`, not in docstrings —
  Typer reads docstrings for help text and the project has none.

## Conventions

- Prompt YAML requires `name`, `description`, and either `template` or `messages`.
  `input_schema` takes either type strings or a JSON Schema object; `output_schema`
  takes JSON Schema only.
- **The type-string language is frozen** at six scalars plus `X | None`. Do not extend
  it — richer types belong in JSON Schema. This is a deliberate boundary, and a PR
  adding generics or constrained forms should be turned down.
- `Prompt.template` is deprecated and warns. Internal code must use `joined_template`
  or `messages`; the suite runs `filterwarnings = ["error"]`, so a deprecated call
  inside the library fails tests.
- Identity is `Prompt.fingerprint`, not `version`. `version` is advisory metadata for
  humans and is deliberately excluded from the fingerprint.
- Anything resolving a path from prompt content goes through `safe_join`, which confines
  after `Path.resolve()`. New path-handling code needs rejection tests, not just
  happy-path ones.
- The Jinja environment uses `StrictUndefined` — an unprovided variable is an error,
  never an empty string. Keep it that way.
- Engines are constructed by the caller and passed into `run_prompt`; the runner never
  builds an engine itself. Only the CLI maps engine names to classes.
- Engines split into a pure layer and a transport layer. `build_params`,
  `parse_response`, and `map_error` are module-level pure functions; `_complete` and
  `_acomplete` are thin and both real. Never derive one from the other by driving an
  event loop — it breaks inside any caller that already has one. Test the pure layer
  directly; it needs no network and no transport mock.
- `BaseEngine` uses an implement-either protocol: a subclass provides `_complete` (new)
  or `generate` (legacy) and the base derives the rest. Legacy engines get
  `usage.estimated = True`.
- Retry is a constructor option on the engine, not a wrapper. Caching and event
  listeners are options on `run_prompt`. There is no middleware pipeline and one is not
  wanted — see the rationale in ARCHITECTURE.md.
- Anything container-like must be tested with `is not None`, never truthiness. A
  `MemoryCache` defines `__len__`, so an empty one is falsy.
- **No `# type: ignore` comments.** The package has zero, and that is intentional —
  the no-comments rule covers directives. Restructure the code instead (see
  `core/jsonschema.py` for `GenericAlias` and `Literal.__getitem__` in place of
  ignores).
- Anything added to `promptkit/__init__.__all__` is public API and needs a changelog
  entry plus docs.

## CLI

`main.py` only assembles the app; every command is its own module under
`cli/commands/` exposing `register(app)`. Shared options and helpers live in
`cli/shared.py`, variable handling in `cli/vars.py`.

Variables come from `--set key=value` (repeatable), `--vars` JSON, and `--vars-file`.
`--set` coerces against the declared schema type, falling back to a guess only for
undeclared fields — never guess when the schema knows better. `--name` and `--context`
are deprecated aliases scheduled for removal in phase 7.

Registry discovery excludes `_`-prefixed directories (partials) and `*.evals.yaml`
(eval suites). Anything else added next to prompts needs the same treatment.

## Engines

Engines wrap official provider SDKs, each behind an extra (`promptkit-core[openai]` and
so on). The base install has **no HTTP client** — do not add one back. Importing an
engine module always works; constructing one without its extra raises
`EngineNotFoundError` naming the exact `pip install`.

The OpenAI and Anthropic SDKs use **`httpx2`**; Ollama uses **`httpx`**. Transport tests
inject a `MockTransport` through the SDK's own `http_client` parameter — do not reach for
`respx`, which patches `httpx` and therefore cannot see the first two. Tests cannot make
network calls: `tests/conftest.py` blocks `connect` and `getaddrinfo` outside localhost.

Anything printed through Rich that contains untrusted or bracketed text must go through
`rich.markup.escape` — `[openai]` is valid Rich markup and will silently vanish.

## CI

Six parallel jobs gate every PR behind a single `ci-ok` check: `lint`, `typecheck`,
`test` (3.10-3.13 on Ubuntu, macOS, Windows), `minimum-dependencies`, `base-install`,
and `build`. `uv.lock` pins CI; run `make lock` after changing dependencies.

`minimum-dependencies` resolves every declared version floor to its lowest and runs the
suite. Treat a failure there as a real bug: the floor is wrong, or the code uses an API
newer than it claims. All GitHub Actions are pinned to commit SHAs — Dependabot bumps
them.

## Git

- Default branch is `dev`; `main` is the release branch.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
- Keep `CHANGELOG.md` current under `## [Unreleased]` (Keep a Changelog format).
- **Never commit or push unless explicitly asked.**

## Pricing

`promptkit/data/pricing.json` is generated — never edit it by hand. Run
`make pricing-refresh`; `make pricing-check` fails when it is stale, and a weekly
workflow opens a PR.

Lookup resolves exactly three ways: exact key, dated/`-latest` snapshot of a key, or a
registered override. **Do not add prefix matching back.** It once priced
`claude-opus-4-5` as `claude-opus-4` — 3x too high — which is worse than reporting
nothing. An unknown model must return `None`.

## Evals and cassettes

A cassette key covers the rendered messages and sampling options — **not the engine or
model**, because replay happens with no engine at all. The model is stored in the entry.
If you change the key, every committed cassette goes stale.

`promptkit test` and the pytest plugin both prefer replay and only build an engine on a
cassette miss, so an offline run needs no credentials. Keep it that way.

## The codemod

`promptkit/codemod.py` writes to other people's source. Two rules:

- **Only rewrite what is unambiguous.** A token like `get_model_pricing` is unique and
  safe. An attribute like `.template` is not — it belongs to Django responses and Jinja
  environments too, so it goes on the review list instead. When in doubt, flag it.
- **Never write blind.** The dry run prints a unified diff, and `--write` is opt-in.

## Docs site

Published at **promptkit-core.ochotzas.com** (GitHub Pages with a custom domain).
`docs/CNAME` must stay in the repo or the domain drops on deploy.

The prompt JSON Schema has two copies on purpose: `promptkit/schemas/prompt.schema.json`
ships in the wheel, and `docs/schemas/prompt.schema.json` is what the `$id` URL resolves
to. `test_docs_copy_matches_the_packaged_schema` fails if they drift — update both, and
keep `$id` in step with `site_url` in `mkdocs.yml`.

## Performance

Two caches matter and both were added after benchmarks showed the cost:

- Compiled input-schema models are cached in `core/schema.py`. Do not rebuild a Pydantic
  model per validation — it cost 24x more than the rendering it guarded.
- `PromptRegistry` caches its path listing as well as its parsed prompts. Do not call
  `paths()` in a loop; it re-globs when refreshed.

Run `make bench` before and after anything touching render, validation, or registry
load.

## Release

Version lives only in `promptkit/__init__.py:__version__` (hatch reads it from there).
Publishing is triggered by a published GitHub release; CD verifies the tag matches
`__version__` and that `CHANGELOG.md` has a matching section.
