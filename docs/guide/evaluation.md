# Evaluation

Prompts regress silently. An eval suite makes that a failing build.

## A suite

Put it next to the prompt as `<name>.evals.yaml`:

```yaml
cases:
  - name: mentions_the_product
    inputs:
      product: Acme Cloud
      message: My invoice looks wrong.
      order_id: A-1042
    assert:
      - contains: Acme Cloud
      - max_tokens: 400

  - name: handles_a_missing_order_id
    inputs:
      product: Acme Cloud
      message: I cannot log in.
    assert:
      - not_contains: order id
      - max_latency: 30

  - name: not_ready_yet
    skip: true
    inputs:
      product: Acme Cloud
      message: ...
```

```bash
promptkit test support_reply.yaml
promptkit test prompts/            # every suite in the tree
```

## Assertions

| Assertion | Passes when |
| --- | --- |
| `contains` | The output contains the string, or every string in a list |
| `not_contains` | The output contains none of them |
| `regex` | The pattern matches (multiline) |
| `equals` | The stripped output equals the value exactly |
| `is_json` | The output parses as JSON (`false` asserts it does not) |
| `json_schema` | The output parses and validates against the schema |
| `max_latency` | The call finished within N seconds |
| `max_cost` | The call cost at most N dollars |
| `max_tokens` | At most N completion tokens were generated |
| `judge` | Another model answers PASS to your requirement |

```yaml
assert:
  - contains: [invoice, total]
  - regex: '^Dear \w+'
  - json_schema:
      type: object
      required: [total]
      properties:
        total: { type: number }
  - judge: The reply is polite and does not promise a refund.
```

`max_cost` passes when the model's pricing is unknown, rather than failing on a number
it cannot compute.

## The judge

`judge` asks a model to grade the output PASS or FAIL. Use a separate engine for it:

```python
from promptkit.evals import run_suite

result = run_suite(prompt, suite, engine, judge_engine=cheaper_engine)
```

A judge is a model, with all that implies. Use it for qualities a regex genuinely cannot
express, and prefer deterministic assertions everywhere else.

## In CI

```bash
promptkit test prompts/ --format junit --output results.xml
```

`promptkit test` exits non-zero when any case fails, so it gates a build like any other
test step.

```yaml
- name: Prompt evals
  run: promptkit test prompts/ --format junit --output results.xml
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Cassettes: run evals for free

Evals call real models, which costs money and is not repeatable. Record the responses
once and replay them forever:

```bash
promptkit test greet.yaml --record        # calls the provider, saves the responses
promptkit test greet.yaml                 # replays them, offline and free
```

The recording lands next to the suite as `greet.cassette.json`. **Commit it** — it is
what lets the evals run in CI with no API key and no cost.

A cassette entry is keyed on the rendered messages and the sampling options, so editing
the prompt or a case's inputs invalidates it. When that happens the failure says so:

```
greet.cassette.json has 2 recording(s) but none for this call. The prompt or the
case inputs changed since it was recorded. Re-record with:
promptkit test <prompt> --record
```

That is the behaviour you want — a prompt change should force you to look at the new
output rather than silently reusing the old one.

| Flag | Effect |
| --- | --- |
| *(none)* | Replay if recorded, otherwise call the provider and record |
| `--record` | Always call the provider and overwrite the recording |
| `--no-cassette` | Always call the provider, record nothing |
| `--cassette PATH` | Use a specific cassette file |

## In pytest

PromptKit ships a pytest plugin, so eval suites run inside your existing test suite:

```bash
pytest prompts/
```

```
prompts/greet.evals.yaml::uses_the_name PASSED
prompts/greet.evals.yaml::stays_short   PASSED
```

Each case becomes a test. With a cassette present it runs offline in milliseconds; with
no cassette and no engine configured it **skips** with a reason rather than failing, so
a contributor without an API key is not blocked.

Re-record from pytest with `--promptkit-record`, and turn collection off entirely with:

```ini
[pytest]
promptkit_evals = false
```

!!! note "Without a cassette, evals call real models"
    They cost money and are not perfectly repeatable. `promptkit test` uses
    `--temperature 0` by default to reduce variance.

## From Python

```python
from promptkit import load_prompt
from promptkit.evals import load_suite, run_suite

prompt = load_prompt("support_reply.yaml")
suite = load_suite("support_reply.evals.yaml")
result = run_suite(prompt, suite, engine, concurrency=8)

result.ok        # False if any case failed
result.passed, result.failed, result.skipped
result.cost      # total across cases

for case in result.results:
    for failure in case.failures:
        print(case.case, failure.kind, failure.detail)
```

Cases run concurrently with a bounded semaphore. An engine error becomes a failed case
carrying the error, not a crash that loses the rest of the run.

## Custom assertions

```python
from promptkit.evals.assertions import AssertionResult, Context, register

@register("mentions_price")
def _mentions_price(context: Context, expected: bool) -> AssertionResult:
    found = "$" in context.completion.text

    return AssertionResult("mentions_price", found is expected)
```

Then use `- mentions_price: true` in a suite. Register before running.
