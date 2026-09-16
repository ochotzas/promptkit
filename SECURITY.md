# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 1.x | Yes |
| 0.1.x | No — please upgrade |

Security fixes land on the latest minor release of the current major version.

The published history is 0.1.0, 0.1.1, then 1.0.0. There are no 0.2-0.6 releases; those
numbers were internal milestones during the rearchitecture and were never uploaded to
PyPI. If you see a package claiming to be one of them, it did not come from us.

## Reporting a vulnerability

Report privately through
[GitHub Security Advisories](https://github.com/ochotzas/promptkit/security/advisories/new),
or by email to me@ochotzas.com.

Please do not open a public issue for a security problem.

Include the affected version, what an attacker can achieve, reproduction steps, and a
minimal prompt file or code sample if one is involved.

Expect an acknowledgement within 72 hours and an assessment within 7 days. Fixes are
released as soon as practical, and reporters are credited in the advisory unless they
ask otherwise.

## Scope

In scope:

- Template injection or sandbox escape through a prompt file
- Path traversal through prompt or include resolution
- API keys leaking into logs, exception messages, or cached data
- Arbitrary code execution from loading a prompt file
- Dependency vulnerabilities reachable through PromptKit's own code paths

Out of scope:

- Outcomes produced by a language model, including prompt injection carried in model
  input or output. PromptKit renders and transports text; it does not and cannot
  validate model behaviour.
- Cost incurred by running prompts. Cost estimation is explicitly an estimate.
- Vulnerabilities in provider APIs or SDKs — report those to the provider.

## For users

PromptKit renders prompt files in a Jinja2 sandbox, and resolves includes through a
loader confined to the prompt's directory. Together these make it safe to *render* a
prompt file you did not write.

They do not make it safe to *trust what it says*. A prompt is instructions to a model.
Review prompt content the way you review code.

API keys are read from arguments or environment variables. PromptKit never writes them
to a file and never includes them in log output or exception messages. If you find one
in either, that is a vulnerability — please report it.
