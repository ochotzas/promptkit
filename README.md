<div align="center">

# ⚙️ PromptKit

**Lint and test your LLM prompts before they reach production.**

A typo in a prompt is a bug. PromptKit catches it like one.

[![PyPI](https://img.shields.io/pypi/v/promptkit-core.svg?style=flat-square&color=4c1)](https://pypi.org/project/promptkit-core/)
[![Python](https://img.shields.io/badge/python-3.10–3.13-blue?style=flat-square)](https://pypi.org/project/promptkit-core/)
[![CI](https://img.shields.io/github/actions/workflow/status/ochotzas/promptkit-core/ci.yml?branch=main&style=flat-square&label=tests)](https://github.com/ochotzas/promptkit-core/actions/workflows/ci.yml)
[![mypy strict](https://img.shields.io/badge/mypy-strict-2a6db2?style=flat-square)](https://mypy-lang.org/)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

[**Documentation**](https://promptkit-core.ochotzas.com/) · [Getting started](https://promptkit-core.ochotzas.com/getting-started/) · [Issues](https://github.com/ochotzas/promptkit-core/issues)

</div>

<table>
<tr><th width="50%">Prompts as f-strings</th><th width="50%">Prompts as data</th></tr>
<tr><td valign="top">

```python
prompt = f"""You are a support agent
for {product}. Be concise.

Customer wrote: {message}
"""
if order_id:
    prompt += f"Order: {order_id}"

msg = {"role": "user", "content": prompt}
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[msg],
)
text = resp.choices[0].message.content
```

Logic tangled with copy. A typo in
`{prodcut}` ships silently. No system
role, no review, no tests, no idea what
it costs until the invoice arrives.

</td><td valign="top">

```yaml
name: support_reply
description: Support reply, house style
version: 1.0.0
messages:
  - role: system
    template: |
      You are a support agent for
      {{ product }}.
      {% include '_partials/style.j2' %}
  - role: user
    template: |
      Customer wrote: {{ message }}
input_schema:
  product: str
  message: str
```

Reviewable in a pull request. A typo is
a **lint error**. Real roles, a shared
house style, and `promptkit cost`
before you spend anything.

</td></tr>
</table>

## Install

```bash
pip install 'promptkit-core[openai]'      # or [anthropic] · [ollama] · [all]
```

The base install ships **no HTTP client and no provider SDK**. Loading, rendering,
validation, composition, linting and cost estimation all work with nothing
network-shaped in your dependency tree.

## Catch the typo before you pay for it

Fat-finger it — `{{ prodcut }}` in the template while the schema still says `product`.
An f-string would ship that to production. Here it does not get past the gate:

```console
$ promptkit lint support_reply.yaml
support_reply
  PK001 'prodcut' is used but not declared (prodcut)
  PK002 'product' is declared but never used (product)

2 finding(s)
```

Exit code 1, so CI stops. Fix it, and the rest of the loop is free and offline:

```console
$ promptkit lint support_reply.yaml
✓ support_reply

$ promptkit render support_reply.yaml --set product=Acme --messages
system
You are a support agent for Acme.
Answer in plain language. Prefer short sentences.

user
Customer wrote: placeholder

$ promptkit cost support_reply.yaml --model gpt-4o-mini
support_reply with gpt-4o-mini
Input tokens: 21 (exact)
Output tokens: 500 (assumed)
Estimated cost: $0.000303
```

Anything you leave out is filled with a placeholder, so you can render and price a
prompt before you have real inputs. Not one of those commands needed an API key.

## From Python

```python
from promptkit import load_prompt, run_prompt
from promptkit.engines.openai import OpenAIEngine

prompt = load_prompt("support_reply.yaml")

with OpenAIEngine() as engine:
    completion = run_prompt(prompt, {"product": "Acme", "message": msg}, engine)

completion.text  # the reply
completion.usage.prompt_tokens  # 241, straight from the provider
completion.usage.estimated  # False — measured, never quietly guessed
engine.cost_of(completion)  # 8.895e-05
```

Need JSON back? Hand it a Pydantic model and get a validated object, with automatic
re-prompting when the model gets it wrong:

```python
result = run_structured(prompt, inputs, engine, output_model=Invoice)
result.value.total  # a float, and your type checker knows it
```

## What you get

| | |
| --- | --- |
| **Catch it before you pay** | Nine lint rules with codes — undeclared variables, unused schema fields, unresolved includes. `--strict` and `--format json` for CI |
| **Evals that gate a build** | `contains`, `regex`, `json_schema`, `max_cost`, `max_latency`, and an LLM `judge`. JUnit output, concurrent, non-zero on failure |
| **Honest costing** | Token counts come from the provider. `Usage.estimated` says when a number was guessed, so a cost report can never quietly lie |
| **One house style** | Share text across prompts with `{% include %}`. Edit the partial and every dependent prompt changes fingerprint, so caches invalidate correctly |
| **A prompt is not code** | Templates render in a Jinja sandbox; includes resolve through a confined loader. Traversal, symlink escapes and `__class__` tricks are refused, with tests to prove it |
| **Identity that means something** | Prompts are identified by a fingerprint over messages, schemas and resolved includes — not a version string someone forgot to bump |
| **Providers, plugged in** | OpenAI, Anthropic, Ollama, and any OpenAI-compatible endpoint. One error hierarchy, so `except RateLimitError` means the same thing everywhere |
| **Ship your own engine** | Register through the `promptkit.engines` entry point from your own package. No PR to this repo |

## The CLI

| | |
| --- | --- |
| `run` | Render and send. `--stream`, `--structured` |
| `render` | Render locally. Free, offline, no key |
| `lint` | Nine rules. `--strict`, `--format json` |
| `test` | Run eval suites. `--format junit` |
| `diff` | Compare two prompts by fingerprint |
| `info` · `list` | Inspect one prompt, or a whole tree |
| `cost` | Token counts and cost before you spend |
| `init` · `engines` | Scaffold a prompt · see what's installed |

Variables come from `--set key=value`, `--vars '{"json": true}'`, or `--vars-file`.
`--set` coerces to the type your schema declares.

## Not an agent framework

Tool calling, agent loops, conversation memory and RAG are **permanently out of scope** —
a boundary, not a gap. Nothing traps you: `engine.client` is the real SDK client and
`completion.raw` the real provider response, so dropping down is one attribute away.

## Coming from 0.1.x

Your prompt files load unchanged — asserted per-file by the test suite. Most code needs
two edits, and a codemod handles the mechanical ones:

```bash
python -m promptkit.codemod your_package/          # dry run, prints a diff
python -m promptkit.codemod your_package/ --write  # apply it
```

Details in the [upgrade guide](https://promptkit-core.ochotzas.com/upgrading/).

---

<div align="center">

**[promptkit-core.ochotzas.com](https://promptkit-core.ochotzas.com/)**

[Prompt files](https://promptkit-core.ochotzas.com/guide/prompt-files/) · [Schemas](https://promptkit-core.ochotzas.com/guide/schemas/) · [Composition](https://promptkit-core.ochotzas.com/guide/composition/) · [Structured output](https://promptkit-core.ochotzas.com/guide/structured-output/) · [Evaluation](https://promptkit-core.ochotzas.com/guide/evaluation/) · [Writing an engine](https://promptkit-core.ochotzas.com/guide/custom-engines/)

MIT licensed · [Contributing](CONTRIBUTING.md) · [Architecture](ARCHITECTURE.md)

<sub>If PromptKit saves you a debugging session, a ⭐ helps others find it.</sub>

</div>
