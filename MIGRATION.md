# Migration plan: 0.1.1 to 1.0

The path from the current codebase to the design in [ARCHITECTURE.md](ARCHITECTURE.md),
as seven phases. Each phase is independently shippable and leaves the repository green.
Phases 1 to 3 are non-breaking; the breaking changes are concentrated in phase 4 and
land behind deprecation shims.

Version markers: `0.2.0` after phase 1, `0.3.0` after phase 3, `0.4.0` after phase 4,
`0.5.0` after phase 5, `0.6.0` after phase 6, `1.0.0` after phase 7.

**Only `1.0.0` is published.** The 0.2-0.6 numbers are internal milestones used to track
progress through the rearchitecture; none of them went to PyPI. The published history is
0.1.0 → 0.1.1 → 1.0.0, and `CHANGELOG.md` records the whole rearchitecture under 1.0.0
rather than pretending those intermediate releases happened.

---

## Phase 1 — Packaging and foundations — DONE (0.2.0)

Intended as no behaviour changes. One narrow break was unavoidable; see the note at the
end of this phase.

- [x] Delete `setup.py`. It declares a different distribution name, a different Python
      floor, and four dependencies the code never imports (`openai`, `requests`,
      `tiktoken`, and a stale `pydantic>=2.0.0`). `pyproject.toml` is authoritative.
- [x] Add the missing `__init__.py` to `promptkit/core/`, `promptkit/cli/`, and
      `promptkit/utils/`. These currently resolve only as implicit namespace packages.
- [x] Add `promptkit/py.typed` and include it in the wheel, so consumers actually get
      the type hints the codebase already has.
- [x] Move `promptkit/tests/` to a top-level `tests/`. Tests are currently installed
      into every user's site-packages.
- [x] Add `promptkit/errors.py` with the full hierarchy from ARCHITECTURE.md, and
      convert every raise site in `loader.py`, `schema.py`, `compiler.py`, and the
      engines. Each new type subclasses the third-party exception it replaces for one
      release, so `except yaml.YAMLError` and `except pydantic.ValidationError` keep
      working.
- [x] Fix `Prompt`: drop the dead `__post_init__`, make `_compiler` a module-level
      shared instance rather than a class attribute default, freeze the model.
- [x] Remove the duplicated `_collect_missing_inputs` call in the CLI `render` command.
- [x] Collapse the two pricing tables (`utils/tokens.py` and `engines/openai.py`) into
      a single `promptkit/pricing.py` with an override hook, and refresh the rates — the
      current tables predate the o-series, gpt-4.1, and Claude 3.5/4.
- [x] Write `CONTRIBUTING.md` and `DEVELOPMENT.md`, both of which are currently 0 bytes.
- [x] Add `SECURITY.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `CODEOWNERS`,
      and GitHub issue and pull request templates.
- [x] State the scope boundary from ARCHITECTURE.md in the README — no tool calling, no
      agent loops, no memory, no RAG — before the first contributor asks.
- [x] Fix the README CI badge, which queries `?branch=main` while the default branch is
      `dev`.

**Outcome.** 69 tests (from 22), mypy clean over `promptkit/` and `tests/`, wheel
verified in a clean environment: `py.typed` present, all four subpackages importable,
`tests/` absent. All five example prompts load and render unchanged.

**Deviation — the pydantic shim was not possible.** The plan called for each new error
type to subclass the third-party exception it replaces. That holds for
`PromptNotFoundError` (`FileNotFoundError`), `PromptParseError` (`yaml.YAMLError`),
`TemplateError` (`jinja2.TemplateError`), and `SchemaError` (`ValueError`). It does not
hold for pydantic: `pydantic.ValidationError` cannot be subclassed alongside
`PromptKitError` without an MRO conflict, and it has no constructible `__init__`.
`InputValidationError` therefore subclasses `ValueError` — as pydantic's own does —
exposes the original through `.cause`, and forwards `.errors()`. Callers writing
`except pydantic.ValidationError` must change; callers writing `except ValueError` do
not. This is recorded as Breaking in the changelog.

**Carried forward from phase 3.** Engines gained `close()` and context manager support
early, since the classes were being restructured anyway. `__del__` was deliberately
left in place so resource behaviour is unchanged; phase 3 removes it.

**Found, not fixed.** `ruff check` reports 76 findings under current ruff defaults, so
CI lint is red on any fresh install — there is no `[tool.ruff]` config pinning the rule
set. Phase 2 owns this.

---

## Phase 2 — Toolchain and CI/CD — DONE

- [x] Replace black and isort with `ruff format` and ruff's import sorting. One tool,
      one config, roughly an order of magnitude faster. Update `make format`, `make
      lint`, and `.pre-commit-config.yaml` together.
- [x] Add an explicit `[tool.ruff.lint]` table: `E`, `F`, `I`, `N`, `UP`, `B`, `A`,
      `C4`, `SIM`, `RUF`, plus `S` (bandit) on the library and `PT` on tests.
- [x] Tighten mypy to `strict = true` and add `warn_unreachable`.
- [x] Adopt `uv` for dependency resolution and add `uv.lock` for reproducible CI.
- [x] CI matrix: Python 3.10 through 3.13 on Ubuntu, macOS, and Windows, with a
      pydantic-lowest-supported job to catch accidental use of newer pydantic APIs.
- [x] Add a base-install job that installs `promptkit` with no extras and asserts the
      core imports, renders, lints, and diffs with no provider SDK present. This is the
      guard on the dependency policy and it must exist before phase 5 adds extras.
- [x] Split CI into parallel `lint`, `typecheck`, `test`, and `build` jobs; cache
      dependencies; upgrade `codecov-action` to v4 with OIDC.
- [x] Add a coverage floor (start at the measured baseline, ratchet up; do not fail the
      build on a number that was never met).
- [x] Replace the long-lived `PYPI_API_TOKEN` in `cd.yml` with PyPI Trusted Publishing
      (OIDC, `id-token: write`), and add Sigstore build provenance attestation.
- [x] Pin all GitHub Actions to commit SHAs and enable Dependabot for actions and
      Python dependencies.
- [x] Add a release workflow that verifies the tag matches `__version__` and that
      `CHANGELOG.md` has an entry for it.
- [x] Add an OpenSSF Scorecard workflow and the badge.

**Outcome.** ruff replaces black and isort with an explicit 12-rule-set config; mypy
runs `strict = true`; `uv.lock` pins CI; the matrix is 12 combinations (3.10-3.13 across
Ubuntu, macOS, Windows) split into parallel `lint`, `typecheck`, `test`,
`minimum-dependencies`, `base-install`, and `build` jobs behind one `ci-ok` gate. All 32
action references across four workflows are pinned to commit SHAs. PyPI publishing moved
to Trusted Publishing with build provenance attestation. Coverage floor set to 80%
against a measured 84%.

**The `minimum-dependencies` job earned its place immediately.** It found three real
defects that the normal matrix could never see, because every declared floor was wrong:

1. `pyyaml>=6.0` cannot build on Python 3.12+ (the Cython 3 incompatibility fixed in
   6.0.1). The floor was raised to `>=6.0.1`.
2. `create_schema_model` called `create_model` with a bare type for required fields.
   Pydantic accepts this now but rejected it in 2.5 — the declared floor. Fixed to the
   canonical `(type, ...)` form, which works across all of 2.x.
3. `typer>=0.9` with modern Click raises `DeprecationWarning` on import of
   `typer.testing`, which `filterwarnings = ["error"]` turned into a collection error.
   The floor was raised to `>=0.12.0` and the third-party warning scoped to an ignore,
   rather than forcing a very recent typer on everyone for a CLI-only dependency.

Engine tests were added alongside the coverage floor — the existing `_payload`,
`_map_error`, `_content`, and `_raise_for_status` helpers are pure and testable with no
network. Coverage went from 68% to 84%, tests from 69 to 101.

**Not done:** `.git-blame-ignore-revs` for the reformat commit, since nothing is
committed yet. Add it when the phase-2 commit lands.

---

## Phase 3 — Sans-I/O engine core and the Completion type — DONE (0.3.0)

The first phase with user-visible API surface, all additive.

- [x] Add `promptkit/types.py`: `Role`, `Message`, `Usage`, `Completion`, `Chunk`.
      `Completion.__str__` returns `.text`, so existing string interpolation survives.
- [x] Split each engine into a pure layer and a transport layer: `build_params`,
      `parse_response`, and `map_error` are module-level pure functions; `complete` and
      `acomplete` are each about ten lines of build-call-parse over them. This removes
      the duplicated request bodies in `engines/openai.py`, where the two paths have
      already drifted — the sync one handles `KeyError`, the async one does not.
- [x] Do **not** derive sync from async. A synchronous method that drives a private
      event loop fails inside any caller that already has one running — a notebook, a
      FastAPI handler, an async test. Both transports are real implementations over the
      shared pure layer.
- [x] Unit-test the pure layer with no network and no mocking of transports. This is
      where engine coverage should concentrate.
- [x] Give engines explicit lifecycle: `close()` / `aclose()` and both context manager
      protocols. Delete the `__del__` cleanup and stop constructing a fresh
      `AsyncClient` per async call.
- [x] Add `Capabilities` flags and read real `usage` from provider responses.
- [x] `run_prompt` returns `Completion`; keep `run_prompt_text` returning `str` for
      callers who want the old shape.
- [x] Add retry as a base-class constructor option — exponential backoff, jitter,
      honours `Retry-After`, on by default — and disable each provider SDK's own retry
      so there is exactly one retry layer.
- [x] Add the `Cache` protocol (`get`, `set`) and a runner `cache=` option keyed on
      prompt fingerprint, inputs, model, and sampling options. API keys never enter the
      key.
- [x] Add `promptkit/events.py`: typed lifecycle events and listener registration.
      Listeners observe and cannot alter the request.
- [x] Do **not** build a middleware pipeline. Three explicit options cover the real
      needs without freezing an extension protocol at 1.0 that no third party has
      pushed on yet. A pipeline remains addable in 1.1; removing one would not be.
- [x] Swap the Jinja `Environment` for a `SandboxedEnvironment` and move the compiled
      template cache to module level, keyed by template hash.

**Outcome.** 200 tests (from 101), coverage 90% (from 84%), runner at 100%. ruff and
mypy strict clean. The engines' pure layer — `build_params`, `parse_response`,
`map_error`, `extract_error`, `check_response` — is module-level and tested with no
network and no transport mocking at all; the transport methods that remain are about ten
lines each. Sync and async are both real implementations over that shared layer, and the
drift that existed in `engines/openai.py` is gone by construction.

**Back-compat was fully preserved, which the plan did not anticipate.** The plan expected
existing tests to need changes beyond the `str` return. Instead `BaseEngine` uses an
implement-either protocol: a subclass may implement `_complete` (new) or `generate`
(legacy), and the base class derives the other. A legacy `generate`-only engine gets a
`Completion` with `usage.estimated = True`; a modern engine reports real provider counts.
Implementing neither raises `NotImplementedError` naming both options. Only the two tests
asserting a `str` return needed touching.

**`Usage.estimated` was added beyond the plan.** Once real usage arrives from providers,
callers need to know whether a number is measured or guessed — a cost report that cannot
distinguish the two is worse than one that admits it. Every `Usage` carries the flag and
the CLI labels its output accordingly.

**Ollama moved from `/api/generate` to `/api/chat`.** The message-based endpoint is the
correct target now that prompts carry roles, and it returns `prompt_eval_count` and
`eval_count` for real usage. `parse_response` still accepts the old `response` field, so
nothing breaks.

**A bug in this phase's own code, caught during verification.** `MemoryCache` defines
`__len__`, so an empty cache is falsy, and `if cache` in the runner took the wrong branch
and cached the first entry under an empty key. Fixed to `if cache is not None`, with
`test_empty_cache_is_not_treated_as_absent` as the regression test. Worth remembering
whenever a container-like object is used as a feature flag.

**Sandbox.** `SandboxedEnvironment` replaces the plain environment, with seven documented
escape vectors as parametrised tests. The compiled-template cache moved to the compiler
instance keyed by SHA-256 of the source, bounded at 512 entries.

**Deferred to phase 5.** Streaming (`stream` / `astream`) raises `NotImplementedError`
with the engine name; `Capabilities.streaming` is `False` everywhere.

**Known gap.** The cache key is built from rendered messages plus model and options,
namespaced by prompt name. It should key on `Prompt.fingerprint`, which phase 4
introduces — switch it there.

**The `minimum-dependencies` job caught a defect this phase introduced elsewhere.**
Phase 2's ruff `UP045` autofix had rewritten the CLI's `Optional[str]` annotations to
`str | None`. Typer resolves its own parameter annotations, and Typer 0.12 — the floor
phase 2 had just set — rejects PEP 604 unions outright. Bisecting showed 0.12 and 0.15
are also incompatible with modern Click (`TyperArgument.make_metavar()` signature
change) and that **0.16.0 is the true floor**; it does support PEP 604, so the modern
annotations stay and no lint exception was needed. Two lessons worth keeping: an
autofix can silently invalidate a version floor set in the same phase, and a floor is
only honest once something actually runs against it.

---

## Phase 4 — Messages, composition, and schema boundaries — DONE (0.4.0)

The breaking phase. Everything here ships with a shim that warns for one minor release.

- [x] Add `MessageTemplate` and change `Prompt.template: str` to
      `Prompt.messages: list[MessageTemplate]`. The loader maps a legacy `template:`
      key to a single user message; `Prompt.template` survives as a deprecated property
      that returns the concatenated messages.
- [x] Add `version` and `metadata` to the prompt schema. `version` is advisory metadata,
      not identity — identity is `fingerprint`.
- [x] Add `Prompt.fingerprint`, a stable hash over resolved messages and schema, which
      the cache and the eval harness both key on.
- [x] Add prompt composition: a confined Jinja loader rooted at the registry directory,
      enabling `{% include %}`, `{% extends %}`, and `{% import %}` across prompt files.
      Directories prefixed with `_` hold partials and are not loaded as prompts.
- [x] Harden the loader: reject absolute paths, reject any path escaping the root after
      normalisation, refuse symlinks pointing outside the root, and cap include depth.
      Each of these gets a test that asserts the rejection, not just the happy path.
- [x] Make `fingerprint` cover resolved includes, so editing a shared partial
      invalidates every dependent prompt's cache.
- [x] **Freeze the type-string language** at the current six scalars plus `X | None`.
      It will not grow generics, constrained forms, or enums. Unparseable type strings
      raise `SchemaError` naming the field.
- [x] Add JSON Schema as the alternative for `input_schema`, and as the only YAML form
      for `output_schema`. Both compile to a Pydantic model internally.
- [x] Add `output_model` so Python callers pass a Pydantic model directly and get an
      inferred result type — the recommended path for typed applications.
- [x] Publish the prompt-file JSON Schema at a stable URL so editors can validate and
      autocomplete prompt YAML.

**Outcome.** 311 tests (from 200), coverage 91%, ruff and mypy strict clean with zero
`type: ignore` comments anywhere in the package. All five legacy example files load
unchanged, asserted per-file by `test_legacy_example_is_unchanged_in_shape`, not by
inspection.

**Back-compat.** `Prompt(template=...)` still works via a before-validator that converts
it to one user message, so no existing construction site breaks. `Prompt.template`
survives as a property that emits `DeprecationWarning`; `joined_template` is the silent
equivalent. Because the suite runs `filterwarnings = ["error"]`, the CLI had to stop
using the deprecated property — which is exactly the pressure that setting is there to
apply.

**Confinement was tested by rejection, not by happy path.** Thirteen traversal vectors
are parametrised (absolute, UNC, drive-qualified, `..` in several positions, embedded
null byte, empty name), plus three symlink cases: a symlinked file escaping the root and
a symlinked directory escaping the root are both rejected, while a symlink staying inside
the root still resolves. Confinement is enforced after `Path.resolve()`, so symlinks
cannot be used to step outside.

**A staleness bug caught during verification.** `ConfinedLoader.get_source` originally
returned `None` as Jinja's `uptodate` callable, which tells Jinja the template is
permanently fresh — an edited partial would never be reloaded within a process. Now
returns an mtime check, as `FileSystemLoader` does. Covered by
`test_editing_a_partial_changes_the_render`.

**Rendering needed the root, not just load-time resolution.** Dependency hashing happens
at load, but `{% include %}` also has to resolve at render time. `Prompt.template_root`
carries the root and `compiler_for(root)` memoises one sandboxed compiler per root.

**Type-string freeze.** The six scalars plus `| None` are all that will ever parse.
Anything else raises `SchemaError` naming the field and pointing at JSON Schema. JSON
Schema is detected by `properties`, `$schema`, or a `type` whose value is a real JSON
Schema type name — so `{"type": "str"}` is still read as a type-string mapping.

**The cache key moved to `Prompt.fingerprint`**, closing the gap phase 3 left open.
Editing a shared partial changes the fingerprint and therefore invalidates the cache of
every dependent prompt.

**Deferred to phase 5 as planned.** `output_schema` and `Prompt.output_model()` compile
and validate, but nothing yet asks a model to produce that shape — no JSON mode, no
parse-validate-repair loop, no `ParsedCompletion`.

---

## Phase 5 — Provider SDKs, plugins, and structured output — DONE (0.5.0)

- [x] Rewrite `OpenAIEngine` over the `openai` SDK and add `promptkit[openai]`.
- [x] Add `AnthropicEngine` over the `anthropic` SDK under `promptkit[anthropic]`
      (system prompt is a top-level parameter there, not a message).
- [x] Rewrite `OllamaEngine` over the `ollama` SDK under `promptkit[ollama]`.
- [x] Add `CompatibleEngine` — the `openai` SDK with a custom `base_url`, covering Groq,
      Together, vLLM, LM Studio, and OpenRouter with one implementation.
- [x] Drop `httpx` from the base dependencies. The core no longer makes HTTP calls at
      all; each provider SDK brings its own client.
- [x] Raise `EngineNotFoundError` naming the exact `pip install` command when an engine
      is imported without its extra. Add `promptkit[all]`.
- [x] Map provider SDK exceptions onto the error hierarchy in each engine's `map_error`,
      so `RateLimitError` means the same thing everywhere.
- [x] Expose `Engine.client` and `Completion.raw` so callers can drop to the SDK for
      anything outside PromptKit's scope, without forking.
- [x] Add entry-point discovery for the `promptkit.engines` group; register the built-in
      engines through it so third-party engines are first-class. Add `promptkit engines
      list`.
- [x] Add streaming: `stream` and `astream` on every engine, `--stream` in the CLI.
- [x] Implement structured output: native JSON mode where `capabilities.json_mode` is
      set, otherwise a schema instruction, then the parse-validate-repair loop with
      `max_parse_retries`, returning `ParsedCompletion[T]`.
- [x] Add exact token counting behind the `tiktoken` extra, falling back to the current
      heuristic when it is not installed.

**Outcome.** 360 tests (from 311), coverage 86%, ruff and mypy strict clean. The
prediction held: rewriting the engines was mechanical because phase 3 had already
isolated the pure layer — `build_params`, `parse_response`, and `map_error` changed shape
but the transport methods stayed about ten lines each.

**The base install now has no HTTP dependency at all.** `httpx` is gone from the base
requirements; each provider SDK brings its own client. A clean `pip install
promptkit-core` pulls in no `openai`, `anthropic`, `ollama`, `tiktoken`, `httpx`, or
`httpx2`, and still loads, renders, validates, lints, and costs prompts. The CI
`base-install` job now asserts all six absences.

**The OpenAI and Anthropic SDKs have moved to `httpx2`; Ollama is still on `httpx`.**
This was discovered the hard way: the first transport tests written with `respx` — which
patches `httpx` — silently failed to intercept and made *real calls to the OpenAI API*,
returning a genuine 401. Two consequences were adopted:

1. Transport tests inject `httpx2.MockTransport` (or `httpx.MockTransport` for Ollama)
   through the SDK's own `http_client` parameter. No global patching, no reliance on a
   mocking library tracking SDK internals.
2. `tests/conftest.py` installs an autouse guard that raises on any outbound `connect`
   or `getaddrinfo` outside localhost. `tests/test_no_network.py` verifies the guard
   itself works. A test can no longer reach the network by accident, which is what
   allowed the first mistake to go unnoticed.

`respx` was added as a dev dependency and then removed, since it cannot see `httpx2`.

**Structured output** uses native JSON mode where `capabilities.json_mode` is set, and
otherwise appends a schema instruction. On a parse failure it re-prompts with the
assistant's previous answer and the validation error attached, up to `max_parse_retries`,
emitting `ParseRetried` each time. Output is recovered from bare JSON, fenced JSON, and
JSON embedded in prose.

**A Rich markup bug caught in the base-install check.** `promptkit engines` printed the
install hint as `pip install 'promptkit-core'` — Rich was parsing `[openai]` as a style
tag and swallowing it, producing a command that installs the wrong thing. Every
console interpolation of untrusted text now goes through `rich.markup.escape`, with
`test_install_hint_survives_rich_markup` as the regression test.

**Anthropic does not advertise `json_mode`**, so structured output there goes through the
schema-instruction path rather than a native one. That is deliberate — the SDK's
structured-output support is tool-shaped, and tool calling is out of scope.

---

## Phase 6 — Registry, evals, and the CLI rebuild — DONE (0.6.0)

- [x] Add `PromptRegistry`: directory loading, dotted namespaces, mtime-invalidated
      cache, and it roots the confined template loader from phase 4.
- [x] Add the eval harness — `EvalCase`, the assertion set (`contains`, `not_contains`,
      `regex`, `json_schema`, `latency`, `cost`, `judge`), a concurrent runner, and
      terminal, JSON, and JUnit XML reporters.
- [x] Rebuild the CLI as one module per command under `cli/commands/`. `main.py` only
      assembles the Typer app.
- [x] Replace the hardcoded `--name` and `--context` options with general variable
      input: repeatable `--set key=value`, `--vars` for inline JSON, and `--vars-file`
      for a JSON or YAML file. The current CLI cannot run any prompt whose schema is not
      exactly `{name, context}`, which is the single worst usability bug in the project.
      Keep the old flags as hidden aliases that warn.
- [x] Add commands: `promptkit init` (scaffold a prompt), `promptkit test` (run evals),
      `promptkit diff` (compare two prompt versions), `promptkit engines list`,
      `promptkit pricing list`.
- [x] Make `promptkit lint` a real linter with rule codes — undeclared template
      variables, declared-but-unused schema fields, missing description, no system
      message, unresolved include, unpinned version — and a `--strict` mode plus
      `--format json` for CI.
- [x] Add shell completion (it is currently disabled via `add_completion=False`).

**Outcome.** 475 tests (from 360), coverage 88%, ruff and mypy strict clean. The CLI
went from one 400-line module to ten command modules plus shared helpers, with `main.py`
doing nothing but assembling the app.

**The worst usability bug in the project is fixed.** `promptkit run` and `render` could
only ever supply `name` and `context`, so any prompt with a different schema was
unrunnable from the CLI. Variables now come from repeatable `--set key=value`, `--vars`
JSON, or `--vars-file` (JSON or YAML), applied in that precedence order.

**`--set` is schema-aware, which was not in the plan and turned out to matter.** A first
implementation guessed types from the literal, so `--set price=9.99` produced a float for
a field declared `str` and validation rejected it. Values are now coerced to the declared
type when the schema knows one, and only guessed otherwise.

**The registry was discovering eval suites as prompts.** `greet.evals.yaml` matched the
`*.yaml` glob, failed to parse as a prompt, and broke `promptkit list` for any directory
containing evals. Suites are now excluded by the `.evals` stem, with a regression test.

**A YAML 1.1 trap in eval suites.** A case named `no`, `on`, or `off` parses as a
boolean, and `name: no` failed with a confusing validation error about booleans. Case
names now coerce scalars to strings, so the author gets what they wrote.

**The linter has nine rules with codes** (PK001-PK009), three severities, `--strict` to
promote warnings to failures, `--format json` for CI, and `--rules` to list them. Two of
the shipped examples lint completely clean, which is asserted by test.

**Evals** live next to their prompt as `<name>.evals.yaml`. Assertions are `contains`,
`not_contains`, `regex`, `equals`, `is_json`, `json_schema`, `max_latency`, `max_cost`,
`max_tokens`, and `judge`. The runner is concurrent with a semaphore bound, an engine
failure degrades to a failed case rather than a crash, and reports render as terminal
tables, JSON, or JUnit XML for CI.

**Deprecation.** `--name` and `--context` still work as hidden aliases, print a notice,
and raise `DeprecationWarning`. They are removed in phase 7.

---

## Phase 7 — Documentation, observability, and 1.0 — DONE (1.0.0)

- [x] Migrate `docs/` from Sphinx and Read the Docs to MkDocs Material. Hand-written
      Markdown API pages, since the no-docstrings rule makes autodoc produce empty
      stubs. Delete `.readthedocs.yaml` and `docs/conf.py`, and update the docs workflow
      to build and deploy MkDocs to GitHub Pages.
- [x] Documentation set: getting started, prompt file reference, the schema reference
      (type strings, JSON Schema, and Pydantic models — and when to reach for each),
      composition and partials, engine guide, structured outputs, evaluation guide,
      retry and caching, events and observability, writing a custom engine, CLI
      reference, the scope boundary and what to
      use instead, migration guide from 0.1.x, and a hand-written API reference.
- [x] Add the OpenTelemetry listener behind the `otel` extra: spans per prompt run with
      model, token counts, and cost as attributes, and no prompt content or API keys
      unless explicitly opted in. It doubles as the worked example for custom listeners.
- [x] Add benchmarks for render throughput and registry load time, tracked in CI.
- [x] Write the 0.1.x to 1.0 migration guide and a codemod script for the mechanical
      parts.
- [x] Remove every deprecation shim introduced in phases 3, 4, and 6.
- [x] Freeze the public API, document the semver contract, and tag 1.0.0.

**Outcome.** 509 tests (from 475), coverage 88%, ruff and mypy strict clean with zero
`type: ignore` in the package. Fourteen documentation pages build under `mkdocs build
--strict`. The base install still pulls in no provider SDK and no HTTP client.

**The benchmarks found two real performance bugs on their first run**, which is the best
argument for writing them:

1. `validate_inputs` rebuilt the Pydantic model on every call. Compiled input-schema
   models are now cached by a stable hash of the schema. Validation is ~40x faster, and
   a simple render went from ~98µs to ~7µs — validation had been costing 24x more than
   the rendering it guarded.
2. `PromptRegistry` cached parsed prompts but re-globbed the whole directory tree on
   every lookup, so loading 100 prompts scanned the tree 100 times. The listing is now
   cached, with a re-scan when a lookup misses it so files added later are still found.
   A warm registry load went from ~103ms to ~0.15ms.

**Deprecations removed:** `Prompt.template`, `get_model_pricing`, the CLI's
`--name`/`--context`, and the engine implement-either fallback. The last of these is the
only one that breaks third-party code without a warning cycle — a custom engine must now
implement `_complete` returning a `Completion`. It is the 1.0 contract freeze, it is
documented in the upgrade guide, and `generate` remains as a convenience over
`complete`.

**The codemod** (`python -m promptkit.codemod`) rewrites the mechanical parts and
separately reports what needs judgement — a `run_prompt` result used as a string, a
custom engine, a `pydantic.ValidationError` handler, or a script passing `--name`. Dry
run by default.

**Two module renames** were forced by tooling rather than design: `cli/commands/list.py`
shadowed the builtin, and `cli/commands/test.py` was being collected by pytest's
conventions. They are now `listing.py` and `evaluate.py`; the CLI command names are
unchanged.

---

## Status

**The migration is complete.** All seven phases are done and 1.0.0 is ready to tag.

| Phase | Version | Tests | Coverage |
| --- | --- | --- | --- |
| Start | 0.1.1 | 22 | — |
| 1 — Packaging and foundations | 0.2.0 | 69 | 84% |
| 2 — Toolchain and CI/CD | 0.2.0 | 101 | 84% |
| 3 — Sans-I/O core and Completion | 0.3.0 | 200 | 90% |
| 4 — Messages, composition, schemas | 0.4.0 | 311 | 91% |
| 5 — Provider SDKs and structured output | 0.5.0 | 360 | 86% |
| 6 — Registry, evals, CLI rebuild | 0.6.0 | 475 | 88% |
| 7 — Docs, observability, 1.0 | 1.0.0 | 509 | 88% |

### To tag the release

1. Merge `dev` into `main`.
2. Add the release date to the `## [1.0.0]` heading in `CHANGELOG.md`
   (`## [1.0.0] - YYYY-MM-DD`), then publish a GitHub release tagged `v1.0.0`. The CD
   workflow verifies the tag matches `__version__` and that `CHANGELOG.md` has a
   matching section before building.
3. Configure PyPI Trusted Publishing for `promptkit-core` (repository
   `ochotzas/promptkit`, workflow `cd.yml`, environment `pypi`) and create the `pypi`
   environment in repository settings. **Publishing fails until this is done** — the
   workflow no longer uses an API token.
4. Enable GitHub Pages with the **GitHub Actions** source, and set the custom domain
   to `promptkit.ochotzas.com` in repository settings. A `CNAME` file is committed at
   `docs/CNAME` so it lands in the published artifact too.
5. Point DNS at GitHub Pages: a `CNAME` record for `promptkit` → `ochotzas.github.io`.
   Enable "Enforce HTTPS" once the certificate is issued.
6. Add the phase-2 reformat commit to `.git-blame-ignore-revs` once it exists.

### Landed after the plan was written

Four things were built on top of 1.0 before release, because each removes a real barrier
to someone adopting it:

- **Eval cassettes.** `promptkit test --record` captures provider responses once and
  replays them forever. This is the one that matters: it turns evals from something that
  costs money on every run into something that runs in CI for free.
- **A bundled pytest plugin.** `pytest prompts/` collects every eval case as a test, so
  prompts are tested where tests already live.
- **`promptkit watch`** — re-lint on save, no extra dependency.
- **Registry version pinning** — `support.refund@2.1.0` and `@latest`.

### Deferred distribution work

Not built, and not forgotten. Each is a lever on adoption rather than a feature:

- **A GitHub Action.** Five lines of YAML to lint prompts and run evals on every PR.
  Cassettes make this free, which is what turns it from a nice idea into an easy sell —
  this is now the strongest of the three.
- **A zero-install path.** `uvx promptkit init` and `pipx run promptkit`, documented as
  the first thing a newcomer sees. Cuts time-to-first-command to one line.
- **Launch copy.** Show HN post, r/LocalLLaMA post, newsletter blurbs for PyCoder's
  Weekly and Python Weekly. The demo cast in `scripts/demo/` is the asset they all hang
  off.

### What 1.1 might still hold

- A middleware pipeline, **only** if real extension needs emerge that retry options,
  the cache protocol, and event listeners cannot express.
- Cost budgets as an eval assertion across a whole suite rather than per case.
- Cassette redaction, if anyone records responses containing personal data.

---

## Cross-cutting rules

**Minimalism.** Every abstraction frozen at 1.0 is one that can never be removed. When
a concrete option and a general framework both solve a problem, 1.0 ships the option.

**Deprecation policy.** Nothing is removed without one full minor release emitting a
`DeprecationWarning` that names the replacement. Shims live in `promptkit/_compat.py`
so they are trivial to delete in phase 7.

**Test coverage gates.** No phase merges below the coverage floor set in phase 2. Every
bug fixed gets a regression test. Provider interactions are tested against recorded
cassettes; live API calls run only in a manually triggered workflow.

**Security.** Two ordering constraints are non-negotiable: the Jinja sandbox (phase 3)
lands before composition (phase 4), and composition lands before the registry (phase 6).
A registry that loads prompt files you did not write, rendering through a
non-sandboxed environment with an unconfined include loader, is a template-injection
path. API keys never appear in logs, exception messages, telemetry, or cache keys.

**Scope discipline.** The out-of-scope table in ARCHITECTURE.md is a commitment. Feature
requests for tool calling, agent loops, memory, or RAG are closed with a pointer to
`Engine.client` and `Completion.raw`, which is the supported way to go around PromptKit
rather than through it.

**Documentation debt.** A phase is not done until `CHANGELOG.md` and the affected docs
pages are updated in the same pull request.
