# Lint rules

```bash
promptkit lint prompts/
promptkit lint prompts/ --strict      # warnings fail too
promptkit lint prompts/ --format json # for CI
promptkit lint --rules                # list these
```

`lint` exits non-zero on any **error**, and on any **warning** with `--strict`. `info`
findings never fail.

| Code | Severity | Rule |
| --- | --- | --- |
| `PK001` | error | Template variable is not declared in `input_schema` |
| `PK002` | warning | `input_schema` field is never used by any template |
| `PK003` | error | Include could not be resolved |
| `PK004` | error | Template failed to compile |
| `PK005` | warning | Prompt has no description |
| `PK006` | info | Prompt has no system message |
| `PK007` | info | Prompt version is unpinned |
| `PK008` | warning | Prompt declares no `input_schema` but uses variables |
| `PK009` | warning | Message template is empty |

## PK001 — undeclared variable

```yaml
template: Hello {{ name }} from {{ company }}
input_schema:
  name: str        # company is missing
```

An error because `StrictUndefined` means this fails at render time. Catching it in lint
is the whole point.

## PK002 — unused field

Usually a rename that was only half applied, or a variable removed from the template but
left in the schema.

## PK003 — unresolved include

The include path does not exist under the registry root, or it escapes the root. Paths
are relative to the root, not to the including file.

## PK004 — broken template

Jinja syntax error. Reported alone — the other rules need a parsed template.

## PK005 — no description

The description is what `promptkit list` shows and what a reviewer reads first.

## PK006 — no system message

Informational. A single-template prompt is a legitimate shape; this only notes that the
model is getting no standing instruction.

## PK007 — unpinned version

The version is still the default `0.1.0`. Informational — set a version once a prompt is
in use so changes are legible in review.

## PK008 — variables without a schema

The template interpolates variables but declares no `input_schema`, so nothing is
validated before rendering.

## PK009 — empty message

A message whose template is blank or only whitespace. It is dropped at render time, so
it is usually a mistake. A message that renders empty *conditionally* is fine and is not
flagged.

## In CI

```yaml
- name: Lint prompts
  run: promptkit lint prompts/ --strict
```

JSON output carries each prompt's fingerprint alongside its findings:

```json
{
  "prompt": "greet",
  "fingerprint": "a3f1...",
  "findings": [
    {"code": "PK001", "severity": "error", "message": "'company' is used but not declared", "field": "company"}
  ]
}
```
