from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import meta

from promptkit.core.compiler import compiler_for
from promptkit.core.jsonschema import looks_like_json_schema
from promptkit.core.prompt import DEFAULT_VERSION, Prompt
from promptkit.core.template import ConfinedLoader, referenced_templates
from promptkit.errors import TemplateError

SEVERITIES = ("error", "warning", "info")


@dataclass(frozen=True, slots=True)
class Rule:
    code: str
    severity: str
    summary: str


RULES: dict[str, Rule] = {
    r.code: r
    for r in (
        Rule("PK001", "error", "template variable is not declared in input_schema"),
        Rule("PK002", "warning", "input_schema field is never used by any template"),
        Rule("PK003", "error", "include could not be resolved"),
        Rule("PK004", "error", "template failed to compile"),
        Rule("PK005", "warning", "prompt has no description"),
        Rule("PK006", "info", "prompt has no system message"),
        Rule("PK007", "info", "prompt version is unpinned"),
        Rule("PK008", "warning", "prompt declares no input_schema but uses variables"),
        Rule("PK009", "warning", "message template is empty"),
    )
}


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    severity: str
    message: str
    field: str | None = None

    @property
    def summary(self) -> str:
        return RULES[self.code].summary


def _finding(code: str, message: str, field: str | None = None) -> Finding:
    rule = RULES[code]

    return Finding(code=code, severity=rule.severity, message=message, field=field)


def declared_fields(prompt: Prompt) -> set[str]:
    if looks_like_json_schema(prompt.input_schema):
        properties = prompt.input_schema.get("properties") or {}

        return set(properties)

    return set(prompt.input_schema)


def template_variables(prompt: Prompt) -> set[str]:
    compiler = compiler_for(prompt.template_root)
    found: set[str] = set()

    for message in prompt.messages:
        parsed = compiler.env.parse(message.template)
        found |= meta.find_undeclared_variables(parsed)

    return found


def lint_prompt(prompt: Prompt, root: str | Path | None = None) -> list[Finding]:
    findings: list[Finding] = []
    compiler = compiler_for(prompt.template_root)

    for index, message in enumerate(prompt.messages):
        if not message.template.strip():
            findings.append(
                _finding("PK009", f"message {index} ({message.role}) is empty")
            )

        try:
            compiler.compile_template(message.template)
        except TemplateError as e:
            findings.append(_finding("PK004", str(e)))

            return findings

    used = template_variables(prompt)
    declared = declared_fields(prompt)

    for name in sorted(used - declared):
        findings.append(
            _finding("PK001", f"'{name}' is used but not declared", field=name)
        )

    for name in sorted(declared - used):
        findings.append(
            _finding("PK002", f"'{name}' is declared but never used", field=name)
        )

    if used and not declared:
        findings.append(
            _finding("PK008", f"{len(used)} variable(s) used with no input_schema")
        )

    findings.extend(_include_findings(prompt, root))

    if not prompt.description.strip():
        findings.append(_finding("PK005", "description is empty"))

    if not any(m.role == "system" for m in prompt.messages):
        findings.append(_finding("PK006", "no system message"))

    if prompt.version == DEFAULT_VERSION:
        findings.append(
            _finding("PK007", f"version is the default '{DEFAULT_VERSION}'")
        )

    return findings


def _include_findings(prompt: Prompt, root: str | Path | None) -> list[Finding]:
    template_root = root if root is not None else prompt.template_root

    if template_root is None:
        return []

    loader = ConfinedLoader(template_root)
    compiler = compiler_for(prompt.template_root)
    findings: list[Finding] = []

    for message in prompt.messages:
        for name in referenced_templates(compiler.env, message.template):
            try:
                loader.read(name)
            except TemplateError as e:
                findings.append(_finding("PK003", str(e), field=name))

    return findings


def worst_severity(findings: list[Finding]) -> str | None:
    for severity in SEVERITIES:
        if any(f.severity == severity for f in findings):
            return severity

    return None


def has_errors(findings: list[Finding]) -> bool:
    return any(f.severity == "error" for f in findings)


def to_dict(prompt: Prompt, findings: list[Finding]) -> dict[str, Any]:
    return {
        "prompt": prompt.name,
        "fingerprint": prompt.fingerprint,
        "findings": [
            {
                "code": f.code,
                "severity": f.severity,
                "message": f.message,
                "field": f.field,
            }
            for f in findings
        ],
    }


__all__ = [
    "RULES",
    "SEVERITIES",
    "Finding",
    "Rule",
    "declared_fields",
    "has_errors",
    "lint_prompt",
    "template_variables",
    "to_dict",
    "worst_severity",
]
