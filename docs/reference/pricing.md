# Pricing and cost

PromptKit reports what a call cost, using token counts from the provider and a vendored
table of model rates.

```python
completion = run_prompt(prompt, inputs, engine)

completion.usage.prompt_tokens  # from the provider
completion.usage.estimated  # False when the provider reported them
engine.cost_of(completion)  # None when the model's rates are unknown
```

```bash
promptkit cost greet.yaml --model claude-opus-4-5
promptkit cost --models
```

## Where the rates come from

`promptkit/data/pricing.json` is a snapshot vendored into the package, generated from
[LiteLLM's public model-pricing dataset](https://github.com/BerriAI/litellm) (MIT
licensed). The source and its licence are recorded in the file's `_meta`. There is no
network call at import and no runtime dependency on LiteLLM.

Its `_meta.updated` field is the snapshot date, surfaced by `promptkit cost` and
available as `promptkit.pricing.PRICING_UPDATED`. A scheduled workflow refreshes it and
opens a pull request when rates move, so staleness is visible rather than silent.

```bash
make pricing-refresh    # update the snapshot
make pricing-check      # fail if it is out of date
```

Two entries are curated by hand because upstream dropped them while the models are still
in use: `claude-3-5-sonnet` and `claude-3-5-haiku`. They are listed in `_meta.curated`.

## How a model name is resolved

Lookup is deliberately conservative. A name resolves in exactly three ways:

| Kind | When | Example |
| --- | --- | --- |
| `exact` | The name is a key in the table | `gpt-4o-mini` |
| `snapshot` | The name is a dated or `-latest` variant of a key | `claude-3-5-sonnet-20241022` |
| `override` | You registered it yourself | `register_pricing("my-model", ...)` |

Anything else returns `None`, and PromptKit reports no cost rather than a wrong one.

```python
from promptkit.pricing import lookup

found = lookup("claude-3-5-sonnet-20241022")
found.matched  # 'claude-3-5-sonnet'
found.kind  # 'snapshot'
found.exact  # False — inferred from a dated variant
found.describe()  # "claude-3-5-sonnet (dated snapshot of ...)"
```

!!! warning "Why there is no prefix matching"
    An earlier version resolved any unknown name to its longest matching prefix. That
    looked helpful and was dangerous: `claude-opus-4-5` resolved to `claude-opus-4` and
    reported a cost **three times too high**, and `o3-pro` was priced as `o3`.

    A cost report that is confidently wrong is worse than one that admits it does not
    know. Only dated snapshots — which genuinely share a price with their base model —
    are inferred.

A name that two providers price differently is excluded from the snapshot entirely, for
the same reason.

## Adding a model

```python
from promptkit.pricing import register_pricing

register_pricing("my-finetune", input_per_million=1.5, output_per_million=6.0)
```

Overrides take precedence over the vendored table and apply to dated variants too. Use
this for fine-tunes, private deployments, negotiated rates, or a model newer than the
snapshot.

## Exact token counts

Install `promptkit-core[tokens]` and counts come from `tiktoken` instead of a
heuristic. `promptkit cost` labels which it used.

## Honesty rules

Two things PromptKit will not do:

- **Report a cost it cannot justify.** Unknown model, no number.
- **Pass an estimate off as a measurement.** `Usage.estimated` is `True` whenever counts
  were derived rather than reported, and `RequestCompleted.cost_exact` is `False` when
  the rates came from a snapshot match.

Estimates from `promptkit cost` are, by nature, estimates: the input count is real but
output length is an assumption you control with `--output-tokens`.
