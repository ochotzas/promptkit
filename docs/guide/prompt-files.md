# Prompt files

A prompt file is YAML. The only required fields are `name`, `description`, and either
`template` or `messages`.

```yaml
name: support_reply
description: Drafts a customer support reply in the house style
version: 1.0.0
messages:
  - role: system
    template: You are a support agent for {{ product }}.
  - role: user
    template: |
      A customer wrote: {{ message }}
      Draft a reply.
input_schema:
  product: str
  message: str
  order_id: "str | None"
output_schema: null
metadata:
  tags: [support, customer]
  author: Olger
  model: gpt-4o-mini
```

A JSON Schema for prompt files is published at
[`promptkit.ochotzas.com/schemas/prompt.schema.json`](https://promptkit.ochotzas.com/schemas/prompt.schema.json)
and ships with the package at `promptkit/schemas/prompt.schema.json`.

Point your editor at it for validation and autocomplete. In VS Code with the YAML
extension:

```json
{
  "yaml.schemas": {
    "https://promptkit.ochotzas.com/schemas/prompt.schema.json": [
      "prompts/**/*.yaml",
      "!prompts/**/*.evals.yaml"
    ]
  }
}
```

Or per file, with a modeline at the top of the prompt:

```yaml
# yaml-language-server: $schema=https://promptkit.ochotzas.com/schemas/prompt.schema.json
name: greet
```

## Fields

| Field | Required | What it is |
| --- | --- | --- |
| `name` | yes | Identifier for the prompt |
| `description` | yes | What the prompt does, for humans |
| `version` | no | Advisory version string. **Not** identity — see below |
| `template` | one of | A single Jinja2 template, loaded as one user message |
| `messages` | one of | Ordered message templates with roles |
| `input_schema` | no | Type strings or a JSON Schema object |
| `output_schema` | no | JSON Schema describing the expected output |
| `metadata` | no | Tags, author, model hint. Never affects rendering |

## Messages

`messages` takes an ordered list. Three forms are accepted:

```yaml
messages:
  - role: system            # explicit
    template: Be brief.
  - user: Hello {{ name }}  # shorthand
  - Hello again             # bare string, becomes a user message
```

Valid roles are `system`, `user`, and `assistant`. Anything else is rejected at load.

A message that renders to only whitespace is dropped, which makes conditional messages
easy:

```yaml
messages:
  - role: system
    template: "{% if tone %}Write in a {{ tone }} tone.{% endif %}"
  - role: user
    template: "{{ question }}"
```

## The single-template form

```yaml
name: greet
description: Greets someone
template: Hello {{ name }}
input_schema:
  name: str
```

This is loaded as one `user` message. It is fully supported, not deprecated — use it
when a prompt genuinely has no system instruction.

## Templating

Templates are Jinja2 with two deliberate settings:

- **`StrictUndefined`** — an unprovided variable is an error, never an empty string.
  Silent empty interpolation is the exact bug PromptKit exists to prevent.
- **Sandboxed** — templates cannot reach attributes like `__class__` or call arbitrary
  Python, so rendering a prompt file you did not write is safe.

Everything else works: `{% for %}`, `{% if %}`, filters, `{% include %}`.

```yaml
template: |
  Summarise these items:
  {% for item in items %}
  - {{ item.title }} ({{ item.count }})
  {% endfor %}
  {% if audience %}Write for {{ audience }}.{% endif %}
```

## Version and fingerprint

`version` is advisory metadata for humans. **Identity is `Prompt.fingerprint`**, a hash
over the messages, schemas, and resolved includes.

```python
a = load_prompt("greet.yaml")          # version: 1.0.0
b = load_prompt("greet-copy.yaml")     # version: 9.9.9, same content

assert a.fingerprint == b.fingerprint  # version is not identity
```

This is what makes caching correct: editing a prompt or one of its partials changes the
fingerprint, which invalidates cached responses. Bumping `version` alone does not.

## Loading and saving

```python
from promptkit import load_prompt, loads_prompt, save_prompt

prompt = load_prompt("prompts/greet.yaml")
prompt = load_prompt("prompts/greet")         # extension optional
prompt = loads_prompt(yaml_text)              # from a string

save_prompt(prompt, "prompts/greet.yaml")
```

`save_prompt` writes `template:` for a single user message and `messages:` otherwise, so
files round-trip in the shape they were written.

## Directories

A directory of prompts becomes a registry with dotted names:

```
prompts/
├── _partials/
│   └── house_style.j2      partial, not a prompt
├── greet.yaml              -> greet
├── greet.evals.yaml        eval suite, not a prompt
└── support/
    └── refund.yaml         -> support.refund
```

```python
from promptkit import PromptRegistry

registry = PromptRegistry("prompts")
registry.names()             # ['greet', 'support.refund']
registry.get("support.refund")
```

Directories prefixed with `_` hold partials. Files ending in `.evals.yaml` are eval
suites. Neither is loaded as a prompt.

The registry caches by mtime, so editing a file on disk is picked up without a restart.

### Versions

When several files declare the same prompt `name` with different `version` values, pin
one with `@`:

```python
registry.get("support.refund")           # by path, as usual
registry.get("support.refund@2.1.0")     # a specific version
registry.get("support.refund@latest")    # the highest version
registry.versions("support.refund")      # {'1.0.0': Path(...), '2.1.0': Path(...)}
```

Versions sort numerically, so `2.10.0` correctly beats `2.1.0`. Asking for a version that
does not exist lists the ones that do.
