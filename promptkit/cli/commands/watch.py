from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated

import typer

from promptkit.cli.shared import console
from promptkit.core.compiler import clear_compilers
from promptkit.core.lint import RULES, lint_prompt
from promptkit.core.loader import load_prompt
from promptkit.core.registry import PromptRegistry, is_eval_suite
from promptkit.errors import PromptKitError

EPILOG = (
    "Examples:\n\npromptkit watch prompts/\n\npromptkit watch greet.yaml --interval 0.2"
)
STYLES = {"error": "red", "warning": "yellow", "info": "dim"}
WATCHED_SUFFIXES = (".yaml", ".yml", ".j2", ".jinja", ".jinja2", ".md", ".txt")


def snapshot(target: Path) -> dict[Path, float]:
    if target.is_file():
        return {target: target.stat().st_mtime}

    found: dict[Path, float] = {}

    for path in target.rglob("*"):
        if path.is_file() and path.suffix in WATCHED_SUFFIXES:
            try:
                found[path] = path.stat().st_mtime
            except OSError:
                continue

    return found


def prompts_in(target: Path) -> list[Path]:
    if target.is_file():
        return [target]

    registry = PromptRegistry(target)

    return [registry.resolve(name) for name in registry.names()]


def check(target: Path) -> tuple[int, int]:
    clear_compilers()
    errors = 0
    findings = 0

    for path in prompts_in(target):
        if is_eval_suite(path):
            continue

        try:
            prompt = load_prompt(path, root=target if target.is_dir() else None)
            results = lint_prompt(prompt, target if target.is_dir() else None)
        except PromptKitError as e:
            console.print(f"[red]✗[/red] {path.name}: {e}")
            errors += 1
            continue

        if not results:
            console.print(f"[green]✓[/green] {prompt.name}")
            continue

        console.print(f"[bold]{prompt.name}[/bold]")

        for finding in results:
            style = STYLES[RULES[finding.code].severity]
            console.print(f"  [{style}]{finding.code}[/] {finding.message}")
            findings += 1

            if finding.severity == "error":
                errors += 1

    return errors, findings


def watch(
    target: Annotated[
        Path, typer.Argument(help="Prompt file or directory to watch")
    ] = Path(),
    interval: Annotated[
        float, typer.Option("--interval", "-i", help="Seconds between checks")
    ] = 0.4,
    once: Annotated[bool, typer.Option("--once", help="Check once and exit")] = False,
) -> None:
    if not target.exists():
        console.print(f"[red]Error: {target} does not exist[/red]")

        raise typer.Exit(1)

    console.print(f"[dim]watching {target} — ctrl-c to stop[/dim]\n")
    errors, _ = check(target)

    if once:
        raise typer.Exit(1 if errors else 0)

    previous = snapshot(target)

    try:
        while True:
            time.sleep(interval)
            current = snapshot(target)

            if current == previous:
                continue

            changed = sorted(
                {
                    path.name
                    for path in set(current) ^ set(previous)
                    | {
                        p
                        for p in set(current) & set(previous)
                        if current[p] != previous[p]
                    }
                }
            )
            previous = current
            console.print(f"\n[dim]— changed: {', '.join(changed)}[/dim]")
            check(target)
    except KeyboardInterrupt:
        console.print("\n[dim]stopped[/dim]")


def register(app: typer.Typer) -> None:
    app.command(help="Re-lint prompts as you edit them.", epilog=EPILOG)(watch)
