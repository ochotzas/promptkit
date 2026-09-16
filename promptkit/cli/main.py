from __future__ import annotations

from typing import Annotated

import typer

from promptkit import __version__
from promptkit.cli.commands import MODULES
from promptkit.cli.shared import console

app = typer.Typer(
    name="promptkit",
    help="Lint and test your LLM prompts before they reach production.",
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

for module in MODULES:
    module.register(app)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"PromptKit version {__version__}")

        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
) -> None:
    return None


if __name__ == "__main__":
    app()
