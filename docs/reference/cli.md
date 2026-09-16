# CLI reference

```bash
promptkit --help
promptkit --version
```

Shell completion: `promptkit --install-completion`.

## Supplying variables

Four commands take variables — `run`, `render`, `cost`, and `test` (through its suite).
Three options, applied in this order, each overriding the last:

```bash
--vars-file inputs.yaml            # JSON or YAML file
--vars '{"name": "Alice"}'         # inline JSON object
--set name=Alice --set age=30      # repeatable key=value
```

`--set` coerces to the type declared in `input_schema`. A field declared `str` keeps
`--set price=9.99` as the string `"9.99"`; a field declared `int` converts it. For
undeclared fields the value is guessed (numbers, `true`/`false`, `null`, JSON arrays and
objects). Everything after the first `=` is the value, so `--set q=a=b` works.

Missing required inputs are filled with placeholders, or prompted for with
`--interactive`.

## `run`

Render a prompt and send it to an engine.

```bash
promptkit run greet.yaml --set question="..."
promptkit run greet.yaml --engine anthropic --model claude-sonnet-4
promptkit run greet.yaml --stream
promptkit run invoice.yaml --structured
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--engine`, `-e` | `openai` | Engine name, from `promptkit engines` |
| `--model`, `-m` | engine default | Model name |
| `--key`, `-k` | `$OPENAI_API_KEY` | API key |
| `--temperature`, `-t` | `0.7` | Sampling temperature |
| `--max-tokens` | none | Cap on generated tokens |
| `--stream` | off | Print tokens as they arrive |
| `--structured` | off | Parse against `output_schema` |
| `--interactive`, `-i` | off | Prompt for missing variables |
| `--verbose`, `-v` | off | Debug logging and full tracebacks |

Prints token usage and cost after the response, labelled `actual` or `estimated`.

## `render`

Render locally. No network, no key, no cost.

```bash
promptkit render greet.yaml --set name=Alice
promptkit render greet.yaml --messages
promptkit render greet.yaml --output rendered.txt
```

`--messages` prints each message with its role — what the provider actually receives.

## `lint`

```bash
promptkit lint greet.yaml
promptkit lint prompts/
promptkit lint prompts/ --strict
promptkit lint greet.yaml --format json
promptkit lint --rules
```

Exits non-zero when any **error** is found, or any **warning** with `--strict`. See
[lint rules](lint-rules.md).

## `test`

Run eval suites. See the [evaluation guide](../guide/evaluation.md).

```bash
promptkit test greet.yaml
promptkit test prompts/ --concurrency 8
promptkit test prompts/ --format junit --output results.xml
```

| Option | Default |
| --- | --- |
| `--concurrency`, `-j` | `4` |
| `--temperature`, `-t` | `0.0` |
| `--format` | `text` (`json`, `junit`) |
| `--output`, `-o` | stdout |
| `--verbose`, `-v` | show passing assertions |
| `--record` | call the provider and record responses to a cassette |
| `--no-cassette` | always call the provider live |
| `--cassette` | use a specific cassette file |

Exits non-zero if any case fails. With a cassette present, runs offline and free — see
[evaluation](../guide/evaluation.md#cassettes-run-evals-for-free).

## `watch`

Re-lint prompts as you edit them.

```bash
promptkit watch prompts/
promptkit watch greet.yaml --interval 0.2
promptkit watch prompts/ --once          # check once and exit, for CI
```

Polls for changes with no extra dependency. `--once` exits non-zero if any error-level
finding is present, so it doubles as a lint gate.

## `info`

```bash
promptkit info greet.yaml
promptkit info greet.yaml --full
```

Name, version, fingerprint, inputs, output schema, includes with digests, tags, and a
preview of each message.

## `cost`

```bash
promptkit cost greet.yaml --model gpt-4o --set name=Alice
promptkit cost --models
```

Counts are exact when `tiktoken` is installed (`promptkit-core[tokens]`), estimated
otherwise. Output tokens are an assumption — `--output-tokens` sets it.

The output names which table entry supplied the rates and the snapshot date. An unknown
model reports no cost rather than guessing — see [pricing](pricing.md).

## `diff`

```bash
promptkit diff v1.yaml v2.yaml
```

Compares messages, schema, and includes. Exits `0` when the fingerprints match, `1` when
they differ, so it works as a check.

## `list`

```bash
promptkit list prompts/
promptkit list prompts/ --tag support
```

Names, versions, descriptions, and eval case counts. Partials and eval suites are not
listed as prompts.

## `init`

```bash
promptkit init greet
promptkit init support/refund --messages --evals
```

| Option | Meaning |
| --- | --- |
| `--dir`, `-d` | Directory to create in |
| `--messages` | Scaffold with system and user messages |
| `--evals` | Also scaffold an eval suite |
| `--force` | Overwrite an existing file |

## `engines`

```bash
promptkit engines
```

Lists every registered engine, whether it is installed, and the exact `pip install` for
the ones that are not.
