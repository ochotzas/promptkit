# Upgrading from 0.1.x

1.0 changes what a prompt *is* and what running one returns. Most code needs two or
three small edits. **Prompt YAML files need no changes at all.**

A codemod handles the mechanical parts:

```bash
python -m promptkit.codemod path/to/your/code          # dry run, prints a diff
python -m promptkit.codemod path/to/your/code --write  # apply it
```

It rewrites only what it can do unambiguously, and reports everything else under
**Needs a human**. Run it on a clean git tree so you can undo it.

!!! note "`.template` is not rewritten automatically"
    `Prompt.template` was removed, but `.template` is a common attribute name on
    unrelated objects — Django responses, Jinja environments, your own classes. The
    codemod flags every `.template` read for you to check rather than rewriting them and
    risking breaking code that has nothing to do with PromptKit.

## Your prompt files still work

Every 0.1.x prompt file loads unchanged. The single-`template:` form is supported, not
deprecated.

```yaml
name: greet
description: Greets someone
template: Hello {{ name }}
input_schema:
  name: str
```

It is loaded as one `user` message. `load_prompt`, `save_prompt`, `render`,
`get_required_inputs`, and `get_optional_inputs` all behave as before.

## `run_prompt` returns a Completion

The one change most code needs.

```python
# 0.1.x
text = run_prompt(prompt, inputs, engine)
if text == "yes":
    ...

# 1.0
completion = run_prompt(prompt, inputs, engine)
if completion.text == "yes":
    ...
```

`str(completion)` returns the text, so f-strings, `print`, and logging are unaffected.
Only `==`, `.startswith`, slicing, and similar need `.text`.

If you want the old shape exactly:

```python
text = run_prompt_text(prompt, inputs, engine)
```

The upside: `completion.usage` carries the provider's real token counts, and
`engine.cost_of(completion)` gives you actual cost rather than an estimate.

## Install the provider extra

The base install no longer includes any provider SDK or HTTP client.

```bash
pip install 'promptkit-core[openai]'      # was: pip install promptkit-core
```

`promptkit engines` shows what is installed and the command for what is not.

## `Prompt.template` is gone

```python
prompt.template          # removed
prompt.joined_template   # the concatenated source
prompt.messages          # what you probably want
```

The `template=` constructor argument and the `template:` YAML key are **not** removed.

## Custom engines implement `_complete`

If you wrote an engine, rename `generate` to `_complete` and return a `Completion`:

```python
# 0.1.x
class MyEngine(BaseEngine):
    def generate(self, prompt: str) -> str:
        return self.client.ask(prompt)

# 1.0
class MyEngine(BaseEngine):
    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        raw = self.client.ask([{"role": m.role, "content": m.content} for m in messages])

        return Completion(
            text=raw.text,
            model=self.model,
            usage=Usage(raw.tokens_in, raw.tokens_out),
            raw=raw,
        )
```

You now receive a list of `Message` with roles rather than one flattened string, and you
report real token usage. See [writing an engine](guide/custom-engines.md).

## Exceptions

Failures now raise PromptKit types. Most subclass what they replace, so existing
handlers keep working:

| You caught | Still works | Prefer |
| --- | --- | --- |
| `FileNotFoundError` | yes | `PromptNotFoundError` |
| `yaml.YAMLError` | yes | `PromptParseError` |
| `jinja2.TemplateError` | yes | `TemplateError` |
| `ValueError` | yes | `SchemaError`, `InputValidationError` |
| `pydantic.ValidationError` | **no** | `InputValidationError` |

Pydantic's exception cannot be subclassed alongside our base class, so this one is a
real break. `InputValidationError` subclasses `ValueError`, exposes the original as
`.cause`, and forwards `.errors()`.

## CLI variables

```bash
# 0.1.x — only ever worked for name and context
promptkit run greet.yaml --name Alice --context demo

# 1.0
promptkit run greet.yaml --set name=Alice --set context=demo
promptkit run greet.yaml --vars '{"name": "Alice"}'
promptkit run greet.yaml --vars-file inputs.yaml
```

`--name` and `--context` are removed. They only ever supported two variable names, so
any prompt with a different schema was unrunnable from the CLI.

## Other removals

| Removed | Use |
| --- | --- |
| `promptkit.utils.tokens.get_model_pricing` | `promptkit.pricing.get_pricing` (per-1M rates, and it moved module) |
| `OllamaEngine(base_url=...)` | `OllamaEngine(host=...)` |
| Engine `__del__` cleanup | `close()`, `aclose()`, or a context manager |

## Worth adopting

None of this is required, but it is why 1.0 exists:

- **`messages:`** with system and user roles instead of one blob
- **`{% include %}`** to share a house style across prompts
- **`promptkit lint`** to catch undeclared variables before you spend a token
- **`promptkit test`** so prompt regressions fail CI
- **`run_structured`** for validated JSON with automatic repair
- **`cache=`** on `run_prompt` to stop paying for identical calls

## If something is missing

Open an issue with your 0.1.x code and what it should do in 1.0. If the codemod should
have handled it, that is a bug worth fixing.
