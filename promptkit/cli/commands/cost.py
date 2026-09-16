from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from promptkit.cli import vars as cli_vars
from promptkit.cli.shared import (
    SetOpt,
    VarsFileOpt,
    VarsOpt,
    console,
    fail,
    open_prompt,
)
from promptkit.errors import PromptKitError
from promptkit.pricing import (
    PRICING_UPDATED,
    estimate_cost,
    format_cost,
    list_models,
    lookup,
)
from promptkit.utils.tokens import estimate_tokens, exact_tokens

EPILOG = (
    "Examples:\n\n"
    "promptkit cost greet.yaml --model gpt-4o --set name=Alice\n\n"
    "promptkit cost --models"
)


def cost(
    prompt_file: Annotated[
        Path | None, typer.Argument(help="Path to a prompt YAML file")
    ] = None,
    model: Annotated[
        str, typer.Option("--model", "-m", help="Model for pricing")
    ] = "gpt-4o-mini",
    output_tokens: Annotated[
        int, typer.Option("--output-tokens", help="Expected output tokens")
    ] = 500,
    set_pairs: SetOpt = None,
    variables: VarsOpt = None,
    vars_file: VarsFileOpt = None,
    models: Annotated[
        bool, typer.Option("--models", help="List models with known pricing")
    ] = False,
) -> None:
    if models or prompt_file is None:
        table = Table(
            title=f"Known model pricing, USD per 1M tokens (snapshot {PRICING_UPDATED})"
        )
        table.add_column("Model", style="cyan")
        table.add_column("Input", justify="right")
        table.add_column("Output", justify="right")

        from promptkit.pricing import get_pricing

        for known in list_models():
            rates = get_pricing(known)

            if rates is not None:
                table.add_row(
                    known,
                    f"{rates.input_per_million:.2f}",
                    f"{rates.output_per_million:.2f}",
                )

        console.print(table)

        return

    prompt = open_prompt(prompt_file)

    try:
        values = cli_vars.collect(
            prompt,
            console,
            set_pairs,
            variables,
            vars_file,
        )
        rendered = prompt.render(values)
    except PromptKitError as e:
        raise fail(e) from e

    counted = exact_tokens(rendered, model)
    input_tokens = counted if counted is not None else estimate_tokens(rendered)
    estimated = estimate_cost(input_tokens, output_tokens, model)
    accuracy = "exact" if counted is not None else "estimated"
    found = lookup(model)

    console.print(f"[bold]{prompt.name}[/bold] with {model}")
    console.print(f"Input tokens: {input_tokens} ({accuracy})")
    console.print(f"Output tokens: {output_tokens} (assumed)")

    if estimated is None or found is None:
        console.print(f"[yellow]No pricing known for '{model}'[/yellow]")
        console.print(
            "[dim]Add it with promptkit.pricing.register_pricing(), or check"
            " promptkit cost --models[/dim]"
        )

        return

    console.print(f"Estimated cost: {format_cost(estimated)}")
    console.print(
        f"[dim]Rates: {found.describe()}"
        f" · {found.pricing.input_per_million}/{found.pricing.output_per_million}"
        f" per 1M · snapshot {PRICING_UPDATED}[/dim]"
    )


def register(app: typer.Typer) -> None:
    app.command(help="Estimate the cost of running a prompt.", epilog=EPILOG)(cost)
