from __future__ import annotations

import typer
from rich.markup import escape
from rich.table import Table

from promptkit.cli.shared import console
from promptkit.engines import plugins

EPILOG = "Examples:\n\npromptkit engines"


def engines() -> None:
    table = Table(title="Engines")
    table.add_column("Name", style="cyan")
    table.add_column("Status")
    table.add_column("Install", style="dim")

    for info in plugins.discover().values():
        status = (
            "[green]ready[/green]" if info.installed else "[yellow]missing[/yellow]"
        )
        table.add_row(info.name, status, escape(info.hint or ""))

    console.print(table)


def register(app: typer.Typer) -> None:
    app.command(help="List the engines available in this installation.", epilog=EPILOG)(
        engines
    )
