# PromptKit

**Lint and test your LLM prompts before they reach production.**

A typo in a prompt is a bug, but nothing treats it like one. PromptKit does: prompts live
in YAML as versioned, reviewable, lintable, testable assets instead of f-strings
scattered through your code.

```bash
pip install promptkit-core[openai]
```

## Why

Hardcoding prompts as f-strings mixes logic with presentation, gives you no validation,
and makes reuse and review difficult. PromptKit treats prompts as data:

- **Declarative** — Jinja2 templates with system, user, and assistant roles
- **Validated** — inputs checked against a schema before anything is sent
- **Composable** — share a house style across prompts with `{% include %}`
- **Testable** — eval suites that fail CI like any other test
- **Typed** — real token usage and cost from the provider, not a guess
- **Safe** — templates render in a sandbox, so a prompt file is not code

## A prompt

```yaml
name: support_reply
description: Drafts a customer support reply in the house style
version: 1.0.0
messages:
  - role: system
    template: |
      You are a support agent for {{ product }}.
      {% include '_partials/house_style.j2' %}
  - role: user
    template: |
      A customer wrote: {{ message }}
      Draft a reply.
input_schema:
  product: str
  message: str
```

## Running it

```python
from promptkit import load_prompt, run_prompt
from promptkit.engines.openai import OpenAIEngine

prompt = load_prompt("support_reply.yaml")

with OpenAIEngine(api_key="sk-...") as engine:
    completion = run_prompt(
        prompt,
        {"product": "Acme Cloud", "message": "My invoice looks wrong."},
        engine,
    )

print(completion.text)
print(completion.usage.prompt_tokens, completion.usage.completion_tokens)
print(engine.cost_of(completion))
```

Or from the terminal:

```bash
promptkit run support_reply.yaml \
  --set product="Acme Cloud" \
  --set message="My invoice looks wrong."
```

## What it does not do

PromptKit is not an agent framework. Tool calling, agent loops, conversation memory, and
retrieval are [permanently out of scope](scope.md) — with an escape hatch to the provider
SDK for when you need them.

## Next

- [Getting started](getting-started.md)
- [Prompt file reference](guide/prompt-files.md)
- [Evaluation](guide/evaluation.md)
- [Upgrading from 0.1.x](upgrading.md)
