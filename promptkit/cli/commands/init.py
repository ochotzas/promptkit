from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from promptkit.cli.shared import console

EPILOG = (
    "Examples:\n\n"
    "promptkit init greet\n\n"
    "promptkit init support/refund --messages --evals"
)

SIMPLE = """name: {name}
description: {description}
version: 0.1.0
template: |
  Hello {{{{ subject }}}}.
input_schema:
  subject: str
"""

WITH_MESSAGES = """name: {name}
description: {description}
version: 0.1.0
messages:
  - role: system
    template: |
      You are a helpful assistant. Answer concisely.
  - role: user
    template: |
      {{{{ question }}}}
input_schema:
  question: str
metadata:
  tags: []
"""

EVALS = """cases:
  - name: answers_the_question
    inputs:
      {field}: example input
    assert:
      - is_json: false
      - max_tokens: 500
"""


def init(
    name: Annotated[str, typer.Argument(help="Prompt name, may include directories")],
    directory: Annotated[
        Path, typer.Option("--dir", "-d", help="Directory to create the prompt in")
    ] = Path(),
    description: Annotated[
        str, typer.Option("--description", help="Prompt description")
    ] = "Describe what this prompt does",
    messages: Annotated[
        bool, typer.Option("--messages", help="Scaffold with system and user messages")
    ] = False,
    evals: Annotated[
        bool, typer.Option("--evals", help="Also scaffold an eval suite")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite an existing file")
    ] = False,
) -> None:
    target = (directory / name).with_suffix(".yaml")

    if target.exists() and not force:
        console.print(f"[red]Error: {target} already exists (use --force)[/red]")

        raise typer.Exit(1)

    target.parent.mkdir(parents=True, exist_ok=True)
    template = WITH_MESSAGES if messages else SIMPLE
    target.write_text(
        template.format(name=target.stem, description=description), encoding="utf-8"
    )
    console.print(f"[green]Created[/green] {target}")

    if evals:
        suite = target.with_name(target.stem + ".evals.yaml")
        suite.write_text(
            EVALS.format(field="question" if messages else "subject"), encoding="utf-8"
        )
        console.print(f"[green]Created[/green] {suite}")


def register(app: typer.Typer) -> None:
    app.command(help="Scaffold a new prompt file.", epilog=EPILOG)(init)
