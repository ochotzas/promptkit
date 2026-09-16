from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape

from promptkit.core.loader import load_prompt
from promptkit.core.prompt import Prompt
from promptkit.core.registry import PromptRegistry
from promptkit.errors import PromptKitError

console = Console()

PromptArg = Annotated[
    Path, typer.Argument(help="Path to a prompt YAML file", show_default=False)
]
SetOpt = Annotated[
    list[str] | None,
    typer.Option("--set", "-s", help="Set a variable as key=value (repeatable)"),
]
VarsOpt = Annotated[
    str | None, typer.Option("--vars", help="Variables as a JSON object")
]
VarsFileOpt = Annotated[
    Path | None, typer.Option("--vars-file", help="Variables from a JSON or YAML file")
]


def fail(error: Exception, verbose: bool = False) -> typer.Exit:
    console.print(f"[red]Error: {escape(str(error))}[/red]")

    if verbose:
        import traceback

        console.print(escape(traceback.format_exc()))

    return typer.Exit(1)


def open_prompt(path: Path, verbose: bool = False) -> Prompt:
    try:
        return load_prompt(path)
    except PromptKitError as e:
        raise fail(e, verbose) from e


def registry_for(path: Path) -> PromptRegistry:
    return PromptRegistry(path if path.is_dir() else path.parent)


__all__ = [
    "PromptArg",
    "SetOpt",
    "VarsFileOpt",
    "VarsOpt",
    "console",
    "fail",
    "open_prompt",
    "registry_for",
]
