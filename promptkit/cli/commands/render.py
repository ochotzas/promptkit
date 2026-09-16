from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from promptkit.cli import vars as cli_vars
from promptkit.cli.shared import (
    PromptArg,
    SetOpt,
    VarsFileOpt,
    VarsOpt,
    console,
    fail,
    open_prompt,
)
from promptkit.errors import PromptKitError

EPILOG = (
    "Examples:\n\n"
    "promptkit render greet.yaml --set name=Alice\n\n"
    'promptkit render greet.yaml --vars \'{"name": "Alice"}\'\n\n'
    "promptkit render greet.yaml --vars-file inputs.yaml\n\n"
    "promptkit render greet.yaml --interactive"
)


def render(
    prompt_file: PromptArg,
    set_pairs: SetOpt = None,
    variables: VarsOpt = None,
    vars_file: VarsFileOpt = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write to this file")
    ] = None,
    messages: Annotated[
        bool, typer.Option("--messages", help="Show each message with its role")
    ] = False,
    interactive: Annotated[
        bool, typer.Option("--interactive", "-i", help="Prompt for missing variables")
    ] = False,
) -> None:
    prompt = open_prompt(prompt_file)

    try:
        values = cli_vars.collect(
            prompt,
            console,
            set_pairs,
            variables,
            vars_file,
            interactive,
        )

        if messages:
            for message in prompt.render_messages(values):
                console.print(f"[bold cyan]{message.role}[/bold cyan]")
                console.print(message.content)
                console.print()

            return

        rendered = prompt.render(values)
    except PromptKitError as e:
        raise fail(e) from e

    if output:
        output.write_text(rendered, encoding="utf-8")
        console.print(f"Rendered prompt saved to {output}")

        return

    console.print(rendered)


def register(app: typer.Typer) -> None:
    app.command(
        help="Render a prompt template with the given variables.", epilog=EPILOG
    )(render)
