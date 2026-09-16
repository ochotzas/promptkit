from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from promptkit.cli.shared import console, fail
from promptkit.core.registry import PromptRegistry
from promptkit.errors import PromptKitError
from promptkit.evals.runner import suite_for

EPILOG = "Examples:\n\npromptkit list prompts/"


def list_prompts(
    directory: Annotated[
        Path, typer.Argument(help="Directory containing prompt files")
    ] = Path(),
    tag: Annotated[
        str | None, typer.Option("--tag", help="Only prompts carrying this tag")
    ] = None,
) -> None:
    registry = PromptRegistry(directory)
    table = Table(title=f"Prompts in {directory}")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="dim")
    table.add_column("Description")
    table.add_column("Evals", justify="right")

    shown = 0

    try:
        for name in registry.names():
            prompt = registry.get(name)

            if tag is not None and tag not in prompt.metadata.tags:
                continue

            suite = suite_for(registry.resolve(name))
            table.add_row(
                name,
                prompt.version,
                prompt.description[:60],
                str(len(suite)) if suite is not None else "[dim]-[/dim]",
            )
            shown += 1
    except PromptKitError as e:
        raise fail(e) from e

    if not shown:
        console.print(f"[yellow]No prompts found in {directory}[/yellow]")

        return

    console.print(table)

    if registry.partials():
        console.print(f"[dim]{len(registry.partials())} partial(s) not listed[/dim]")


def register(app: typer.Typer) -> None:
    app.command(name="list", help="List the prompts in a directory.", epilog=EPILOG)(
        list_prompts
    )
