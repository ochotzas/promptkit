# Contributing to PromptKit

Thanks for taking the time to contribute. PromptKit is MIT-licensed and community-run;
issues, docs fixes, and pull requests are all welcome.

## Before you start

PromptKit is mid-rearchitecture toward 1.0. [ARCHITECTURE.md](ARCHITECTURE.md) describes
the target design and [MIGRATION.md](MIGRATION.md) is the phased plan. If your change is
structural, read both first — the work may already be planned, sequenced, or
deliberately out of scope.

**What PromptKit does not do**, permanently: tool and function calling, agent loops,
conversation memory, and RAG. These are not missing features; they belong to agent
frameworks and provider SDKs. Feature requests for them will be closed with a pointer to
the escape hatches PromptKit provides for reaching the provider directly.

## Setup

```bash
git clone https://github.com/ochotzas/promptkit-core.git
cd promptkit
make install-dev
```

That installs the package in editable mode with dev extras and registers the pre-commit
hooks.

## Making a change

```bash
make format      # ruff check --fix + ruff format
make all         # format, lint, type-check, test — run before pushing
```

Every pull request needs:

- Tests covering the change. A bug fix needs a regression test that fails before it.
- `make all` passing locally.
- A `CHANGELOG.md` entry under `## [Unreleased]`.
- Docs updated in the same PR when behaviour or public API changes.

## Code style

- **No comments, no docstrings.** Names and type annotations carry the meaning. This is
  a deliberate project convention, not an oversight. Narrative explanation belongs in
  `docs/`.
- Full type annotations on every function and method. `mypy` runs with
  `disallow_untyped_defs`.
- Python 3.10+ syntax: `X | None`, `list[str]`, `dict[str, Any]`.
- Anything added to `promptkit.__all__` is public API: it needs a changelog entry, docs,
  and cannot be changed again without a deprecation cycle.

## Errors

Never let a third-party exception escape the public API. Every failure raises a type
from `promptkit/errors.py`. If none fits, add one to the hierarchy rather than raising
a bare `ValueError`.

## Pricing data

`promptkit/pricing.py` holds per-million-token rates and a `PRICING_UPDATED` date.
Provider rates change without notice. If you update a rate, cite the provider's pricing
page in the PR and bump `PRICING_UPDATED`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`,
`refactor:`, `test:`, `chore:`. Target the `dev` branch; `main` is the release branch.

## Reporting bugs

Open an issue with the PromptKit version, Python version, a minimal prompt YAML that
reproduces it, and the full traceback. Security issues go to
[SECURITY.md](SECURITY.md) instead — please do not open a public issue for those.
