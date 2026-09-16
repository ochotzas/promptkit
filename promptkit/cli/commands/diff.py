from __future__ import annotations

import difflib
from pathlib import Path
from typing import Annotated

import typer

from promptkit.cli.shared import console, fail
from promptkit.core.loader import load_prompt
from promptkit.core.prompt import Prompt
from promptkit.errors import PromptKitError

EPILOG = (
    "Examples:\n\n"
    "promptkit diff old.yaml new.yaml\n\n"
    "promptkit diff v1.yaml v2.yaml --messages"
)


def _sections(prompt: Prompt) -> list[str]:
    lines = [
        f"version: {prompt.version}",
        f"description: {prompt.description}",
        "",
    ]

    for index, message in enumerate(prompt.messages):
        lines.append(f"--- message {index} ({message.role}) ---")
        lines.extend(message.template.splitlines())
        lines.append("")

    lines.append("--- input_schema ---")
    lines.extend(f"{k}: {v}" for k, v in sorted(prompt.input_schema.items()))

    if prompt.dependencies:
        lines.append("--- includes ---")
        lines.extend(f"{name}: {digest[:12]}" for name, digest in prompt.dependencies)

    return lines


def diff(
    left: Annotated[Path, typer.Argument(help="First prompt file")],
    right: Annotated[Path, typer.Argument(help="Second prompt file")],
    context_lines: Annotated[
        int, typer.Option("--context", "-c", help="Lines of context")
    ] = 3,
) -> None:
    try:
        first = load_prompt(left)
        second = load_prompt(right)
    except PromptKitError as e:
        raise fail(e) from e

    if first.fingerprint == second.fingerprint:
        console.print("[green]Prompts are identical[/green]")
        console.print(f"[dim]fingerprint {first.fingerprint[:12]}[/dim]")

        return

    console.print(f"[dim]{first.fingerprint[:12]} -> {second.fingerprint[:12]}[/dim]\n")

    lines = difflib.unified_diff(
        _sections(first),
        _sections(second),
        fromfile=str(left),
        tofile=str(right),
        lineterm="",
        n=context_lines,
    )

    for line in lines:
        if line.startswith("+") and not line.startswith("+++"):
            console.print(f"[green]{line}[/green]", highlight=False)
        elif line.startswith("-") and not line.startswith("---"):
            console.print(f"[red]{line}[/red]", highlight=False)
        elif line.startswith("@@"):
            console.print(f"[cyan]{line}[/cyan]", highlight=False)
        else:
            console.print(line, highlight=False)

    raise typer.Exit(1)


def register(app: typer.Typer) -> None:
    app.command(help="Compare two prompt files.", epilog=EPILOG)(diff)
