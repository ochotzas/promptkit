from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table

from promptkit.cli.shared import PromptArg, console, fail, registry_for
from promptkit.core.lint import RULES, lint_prompt, to_dict
from promptkit.core.loader import load_prompt
from promptkit.errors import PromptKitError

EPILOG = (
    "Examples:\n\n"
    "promptkit lint greet.yaml\n\n"
    "promptkit lint prompts/ --strict\n\n"
    "promptkit lint greet.yaml --format json"
)
STYLES = {"error": "red", "warning": "yellow", "info": "dim"}


def lint(
    target: PromptArg,
    strict: Annotated[
        bool, typer.Option("--strict", help="Treat warnings as failures")
    ] = False,
    output_format: Annotated[
        str, typer.Option("--format", help="Output format: text or json")
    ] = "text",
    rules: Annotated[
        bool, typer.Option("--rules", help="List the lint rules and exit")
    ] = False,
) -> None:
    if rules:
        table = Table(title="Lint rules")
        table.add_column("Code", style="cyan")
        table.add_column("Severity")
        table.add_column("Summary")

        for rule in RULES.values():
            table.add_row(
                rule.code, f"[{STYLES[rule.severity]}]{rule.severity}[/]", rule.summary
            )

        console.print(table)

        return

    try:
        reports = _collect(target)
    except PromptKitError as e:
        raise fail(e) from e

    if output_format == "json":
        console.print_json(json.dumps(reports))
    else:
        _print_text(reports)

    failed = any(
        f["severity"] == "error" or (strict and f["severity"] == "warning")
        for report in reports
        for f in report["findings"]
    )

    if failed:
        raise typer.Exit(1)


def _collect(target: Path) -> list[dict[str, Any]]:
    if target.is_dir():
        registry = registry_for(target)

        return [
            to_dict(registry.get(name), lint_prompt(registry.get(name), target))
            for name in registry.names()
        ]

    prompt = load_prompt(target)

    return [to_dict(prompt, lint_prompt(prompt))]


def _print_text(reports: list[dict[str, Any]]) -> None:
    total = 0

    for report in reports:
        findings: list[dict[str, Any]] = report["findings"]

        if not findings:
            console.print(f"[green]✓[/green] {report['prompt']}")
            continue

        console.print(f"[bold]{report['prompt']}[/bold]")

        for finding in findings:
            style = STYLES[finding["severity"]]
            field = f" ({finding['field']})" if finding["field"] else ""
            console.print(
                f"  [{style}]{finding['code']}[/] {finding['message']}{field}"
            )
            total += 1

    if total:
        console.print(f"\n{total} finding(s)")


def register(app: typer.Typer) -> None:
    app.command(help="Check prompt files for problems.", epilog=EPILOG)(lint)
