# Getting started

## Install

The base install has no HTTP client and no provider SDK. Add the provider you use:

=== "OpenAI"

    ```bash
    pip install 'promptkit-core[openai]'
    ```

=== "Anthropic"

    ```bash
    pip install 'promptkit-core[anthropic]'
    ```

=== "Ollama"

    ```bash
    pip install 'promptkit-core[ollama]'
    ```

=== "Everything"

    ```bash
    pip install 'promptkit-core[all]'
    ```

Check what is available:

```bash
promptkit engines
```

## Your first prompt

```bash
promptkit init greet --messages
```

That writes `greet.yaml`:

```yaml
name: greet
description: Describe what this prompt does
version: 0.1.0
messages:
  - role: system
    template: |
      You are a helpful assistant. Answer concisely.
  - role: user
    template: |
      {{ question }}
input_schema:
  question: str
```

## Render without calling a model

Rendering is free and offline. Do this first, always.

```bash
promptkit render greet.yaml --set question="What is a vector database?"
promptkit render greet.yaml --messages
```

`--messages` shows each message with its role, which is what the provider actually
receives.

## Check it

```bash
promptkit lint greet.yaml
promptkit info greet.yaml
promptkit cost greet.yaml --model gpt-4o-mini
```

`lint` catches undeclared variables, unused schema fields, unresolved includes, and
missing metadata before you spend a token on them.

## Run it

```bash
export OPENAI_API_KEY=sk-...
promptkit run greet.yaml --set question="What is a vector database?"
```

Add `--stream` to see tokens as they arrive.

## From Python

```python
from promptkit import load_prompt, run_prompt
from promptkit.engines.openai import OpenAIEngine

prompt = load_prompt("greet.yaml")

with OpenAIEngine() as engine:
    completion = run_prompt(prompt, {"question": "What is a vector database?"}, engine)

print(completion.text)
```

`run_prompt` returns a [`Completion`](reference/api.md#completion), not a string. It
carries the text, the model that answered, real token usage, the finish reason, and the
raw provider response.

## Test it

Create `greet.evals.yaml` next to the prompt:

```yaml
cases:
  - name: answers_briefly
    inputs:
      question: What is a vector database?
    assert:
      - max_tokens: 200
      - not_contains: "I cannot"
```

```bash
promptkit test greet.yaml
```

See the [evaluation guide](guide/evaluation.md) for the full assertion set and CI setup.

## Where to go next

| You want to | Read |
| --- | --- |
| Know every field in a prompt file | [Prompt files](guide/prompt-files.md) |
| Validate richer inputs | [Schemas](guide/schemas.md) |
| Share text between prompts | [Composition](guide/composition.md) |
| Get JSON back reliably | [Structured output](guide/structured-output.md) |
| Add retries or a cache | [Retry and caching](guide/retry-and-caching.md) |
| Trace runs in production | [Observability](guide/observability.md) |
