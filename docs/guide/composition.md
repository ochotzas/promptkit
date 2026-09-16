# Composition

Prompts share text through Jinja's own mechanisms — `{% include %}`, `{% extends %}`,
and `{% import %}` — resolved by a loader confined to the prompt's directory.

## Partials

Directories prefixed with `_` hold partials. They are not loaded as prompts.

```
prompts/
├── _partials/
│   ├── house_style.j2
│   └── safety.j2
├── support/
│   └── refund.yaml
└── greet.yaml
```

`_partials/house_style.j2`:

```jinja
Answer in plain language. Prefer short sentences. If you are unsure, say so
rather than guessing.
```

`greet.yaml`:

```yaml
name: greet
description: Greeting in the house style
version: 1.0.0
messages:
  - role: system
    template: |
      You are a support agent for {{ product }}.
      {% include '_partials/house_style.j2' %}
  - role: user
    template: Hello {{ name }}
input_schema:
  product: str
  name: str
```

Include paths are always relative to the registry root, not to the including file, so a
prompt nested three directories deep still writes `{% include '_partials/house_style.j2' %}`.

## Dependencies and the fingerprint

Resolved includes are recorded on the prompt and folded into its fingerprint:

```python
prompt = load_prompt("prompts/greet.yaml")
prompt.dependencies
# (('_partials/house_style.j2', 'a3f1...'),)
```

Editing a shared partial changes the fingerprint of **every** prompt that includes it,
which is what makes response caching correct. `promptkit info` shows the includes and
their digests.

## Confinement

The template loader is confined to the registry root. It refuses:

- absolute paths (`/etc/passwd`)
- UNC and drive-qualified paths (`\\server\share`, `C:/windows`)
- `..` traversal in any position, including after normalisation
- symlinks — file or directory — that resolve outside the root
- embedded null bytes and empty names
- include chains deeper than 10

Confinement is checked **after** `Path.resolve()`, so a symlink cannot be used to step
outside. A symlink that stays inside the root still works.

Together with the [sandbox](prompt-files.md#templating), this is what makes it safe to
load prompt files you did not write — from a shared repository, a pull request, or a
package.

!!! warning "Trust is still a judgement call"
    The sandbox and the confined loader stop template injection and path traversal. They
    do not stop a prompt from *saying* something harmful to a model. Review prompt
    content the way you review code.

## Choosing a root

By default the root is the prompt file's own directory. Pass `root=` to widen it:

```python
load_prompt("prompts/support/refund.yaml", root="prompts")
```

A `PromptRegistry` does this for you — its root becomes the loader root for every prompt
it loads, which is why partials resolve from anywhere in the tree.

```python
registry = PromptRegistry("prompts")
registry.get("support.refund")   # '_partials/...' resolves
```

## When not to compose

An include is indirection. It earns its place when the same text appears in several
prompts and must change together. A single prompt with one include used nowhere else is
harder to read than the inline version.
