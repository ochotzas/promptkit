from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from promptkit.cli import vars as cli_vars
from promptkit.cli.shared import PromptArg, console, open_prompt
from promptkit.utils.tokens import count_tokens

EPILOG = "Examples:\n\npromptkit info greet.yaml"
PREVIEW_LINES = 10


def info(
    prompt_file: PromptArg,
    full: Annotated[
        bool, typer.Option("--full", help="Show the whole template, not a preview")
    ] = False,
) -> None:
    prompt = open_prompt(prompt_file)

    console.print(f"[bold]{prompt.name}[/bold] [dim]v{prompt.version}[/dim]")
    console.print(prompt.description or "[dim]no description[/dim]")
    console.print(f"[dim]fingerprint {prompt.fingerprint[:12]}[/dim]")
    console.print()

    rows = cli_vars.describe_inputs(prompt)

    if rows:
        table = Table(title="Inputs")
        table.add_column("Field", style="cyan")
        table.add_column("Type")
        table.add_column("Required")

        for field, type_str, required in rows:
            table.add_row(
                field, type_str, "[red]yes[/red]" if required else "[dim]no[/dim]"
            )

        console.print(table)
    else:
        console.print("[dim]no declared inputs[/dim]")

    if prompt.output_schema is not None:
        console.print()
        console.print("[bold]Output schema:[/bold] declared")

    if prompt.dependencies:
        console.print()
        console.print("[bold]Includes:[/bold]")

        for name, digest in prompt.dependencies:
            console.print(f"  {name} [dim]{digest[:12]}[/dim]")

    if prompt.metadata.tags:
        console.print()
        console.print(f"[bold]Tags:[/bold] {', '.join(prompt.metadata.tags)}")

    console.print()
    console.print("[bold]Messages:[/bold]")

    for index, message in enumerate(prompt.messages):
        console.print(f"[cyan]{index}. {message.role}[/cyan]")
        lines = message.template.splitlines()
        shown = lines if full else lines[:PREVIEW_LINES]

        for line in shown:
            console.print(f"  {line}")

        if not full and len(lines) > PREVIEW_LINES:
            console.print(f"  [dim]... {len(lines) - PREVIEW_LINES} more lines[/dim]")

    console.print()
    console.print(f"[dim]~{count_tokens(prompt.joined_template)} template tokens[/dim]")


def register(app: typer.Typer) -> None:
    app.command(
        help="Display detailed information about a prompt file.", epilog=EPILOG
    )(info)
