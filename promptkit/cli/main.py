"""
Command-line interface for PromptKit.

This module provides a comprehensive CLI for working with prompts,
including running, rendering, and validating prompt files.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

import typer
from rich.console import Console
from rich.table import Table

from promptkit import __version__
from promptkit.core.loader import load_prompt
from promptkit.core.prompt import Prompt
from promptkit.core.runner import run_prompt
from promptkit.engines.ollama import OllamaEngine
from promptkit.engines.openai import OpenAIEngine
from promptkit.utils.logging import configure_logging, get_logger
from promptkit.utils.tokens import estimate_cost, estimate_tokens, format_cost

app = typer.Typer(
    name="promptkit",
    help="Structured Prompt Engineering for LLM Apps",
    add_completion=False,
)
console = Console()
logger = get_logger(__name__)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"PromptKit version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    )
) -> None:
    """PromptKit CLI - Structured Prompt Engineering for LLM Apps."""
    pass


@app.command()
def run(
    prompt_file: Path = typer.Argument(..., help="Path to the prompt YAML file"),
    api_key: Optional[str] = typer.Option(
        None, "--key", "-k", help="OpenAI API key", envvar="OPENAI_API_KEY"
    ),
    model: str = typer.Option("gpt-4o-mini", "--model", "-m", help="Model to use"),
    engine: str = typer.Option(
        "openai", "--engine", "-e", help="Engine to use (openai, ollama)"
    ),
    temperature: float = typer.Option(
        0.7, "--temperature", "-t", help="Temperature (0.0-2.0)"
    ),
    max_tokens: Optional[int] = typer.Option(
        None, "--max-tokens", help="Maximum tokens to generate"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    name: Optional[str] = typer.Option(
        None, "--name", help="Name variable for the prompt"
    ),
    context: Optional[str] = typer.Option(
        None, "--context", help="Context variable for the prompt"
    ),
) -> None:
    """
    Run a prompt with the specified engine and parameters.

    Additional arguments are passed as template variables to the prompt.

    Examples:
        promptkit run greet.yaml --key sk-... --name Alice
        promptkit run greet.yaml --engine ollama --model llama2 --name Bob
    """
    if verbose:
        configure_logging("DEBUG")

    try:
        console.print(f"Loading prompt from {prompt_file}...")
        prompt = load_prompt(prompt_file)

        template_vars: Dict[str, Any] = {}
        if name:
            template_vars["name"] = name
        if context:
            template_vars["context"] = context

        _collect_missing_inputs(prompt, template_vars)
        llm_engine: Union[OpenAIEngine, OllamaEngine]
        if engine.lower() == "openai":
            if not api_key:
                console.print(
                    "[red]Error: OpenAI API key is required for OpenAI engine[/red]"
                )
                console.print(
                    "Set OPENAI_API_KEY environment variable or use --key option"
                )
                raise typer.Exit(1)

            llm_engine = OpenAIEngine(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        elif engine.lower() == "ollama":
            llm_engine = OllamaEngine(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            console.print(f"[red]Error: Unsupported engine '{engine}'[/red]")
            console.print("Supported engines: openai, ollama")
            raise typer.Exit(1)

        rendered_prompt = prompt.render(template_vars)
        input_tokens = estimate_tokens(rendered_prompt)
        estimated_cost = estimate_cost(input_tokens, max_tokens or 500, model)

        if estimated_cost:
            console.print(f"Estimated cost: {format_cost(estimated_cost)}")

        console.print("Generating response...")
        response = run_prompt(prompt, template_vars, llm_engine)

        console.print("\n[bold green]Response:[/bold green]")
        console.print(response)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def render(
    prompt_file: Path = typer.Argument(..., help="Path to the prompt YAML file"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    name: Optional[str] = typer.Option(
        None, "--name", help="Name variable for the prompt"
    ),
    context: Optional[str] = typer.Option(
        None, "--context", help="Context variable for the prompt"
    ),
    variables: Optional[str] = typer.Option(
        None, "--vars", help="JSON string of template variables"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Prompt for missing variables interactively"
    ),
) -> None:
    """
    Render a prompt template with the given variables.

    Examples:
        promptkit render greet.yaml --name Alice
        promptkit render greet.yaml --vars '{"name": "Alice", "context": "Demo"}'
        promptkit render code_review.yaml --interactive
    """
    try:
        prompt = load_prompt(prompt_file)

        template_vars: Dict[str, Any] = {}

        if name:
            template_vars["name"] = name
        if context:
            template_vars["context"] = context

        if variables:
            try:
                json_vars = json.loads(variables)
                if isinstance(json_vars, dict):
                    template_vars.update(json_vars)
                else:
                    console.print("[red]Error: --vars must be a JSON object[/red]")
                    raise typer.Exit(1)
            except json.JSONDecodeError as e:
                console.print(f"[red]Error: Invalid JSON in --vars: {e}[/red]")
                raise typer.Exit(1)

        if interactive:
            _collect_missing_inputs(prompt, template_vars, use_placeholders=False)
        else:
            _collect_missing_inputs(prompt, template_vars, use_placeholders=True)

        _collect_missing_inputs(prompt, template_vars)

        rendered = prompt.render(template_vars)

        if output:
            output.write_text(rendered, encoding="utf-8")
            console.print(f"Rendered prompt saved to {output}")
        else:
            console.print(rendered)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def lint(
    prompt_file: Path = typer.Argument(..., help="Path to the prompt YAML file"),
) -> None:
    """
    Validate a prompt file structure and syntax.

    Examples:
        promptkit lint greet.yaml
    """
    try:
        prompt = load_prompt(prompt_file)

        console.print("[green]✓[/green] Prompt file is valid")

        table = Table(title="Prompt Information")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Name", prompt.name)
        table.add_row("Description", prompt.description)
        table.add_row(
            "Required Inputs", ", ".join(prompt.get_required_inputs()) or "None"
        )
        table.add_row(
            "Optional Inputs", ", ".join(prompt.get_optional_inputs()) or "None"
        )

        console.print(table)

        template_tokens = estimate_tokens(prompt.template)
        console.print(f"\nTemplate complexity: ~{template_tokens} tokens")

    except Exception as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def info(
    prompt_file: Path = typer.Argument(..., help="Path to the prompt YAML file"),
) -> None:
    """
    Display detailed information about a prompt file.

    Examples:
        promptkit info greet.yaml
    """
    try:
        prompt = load_prompt(prompt_file)

        console.print(f"[bold]Prompt: {prompt.name}[/bold]")
        console.print(f"Description: {prompt.description}")
        console.print()

        if prompt.input_schema:
            console.print("[bold]Input Schema:[/bold]")
            for field, type_str in prompt.input_schema.items():
                required = " | None" not in type_str
                status = (
                    "[red]required[/red]" if required else "[yellow]optional[/yellow]"
                )
                console.print(
                    f"  {field}: {type_str.replace(' | None', '')} ({status})"
                )
        else:
            console.print("[bold]Input Schema:[/bold] None")

        console.print()

        console.print("[bold]Template Preview:[/bold]")
        lines = prompt.template.split("\n")
        for i, line in enumerate(lines[:10], 1):
            console.print(f"{i:2d}: {line}")

        if len(lines) > 10:
            console.print(f"... ({len(lines) - 10} more lines)")

        console.print()
        console.print(f"Template length: {len(prompt.template)} characters")
        console.print(f"Estimated tokens: ~{estimate_tokens(prompt.template)}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def cost(
    prompt_file: Path = typer.Argument(..., help="Path to the prompt YAML file"),
    model: str = typer.Option(
        "gpt-4o-mini", "--model", "-m", help="Model for cost estimation"
    ),
    output_tokens: int = typer.Option(
        500, "--output-tokens", help="Expected output tokens"
    ),
    name: Optional[str] = typer.Option(
        None, "--name", help="Name variable for the prompt"
    ),
    context: Optional[str] = typer.Option(
        None, "--context", help="Context variable for the prompt"
    ),
) -> None:
    """
    Estimate the cost of running a prompt.

    Examples:
        promptkit cost greet.yaml --model gpt-4 --name Alice
    """
    try:
        prompt = load_prompt(prompt_file)

        template_vars: Dict[str, Any] = {}
        if name:
            template_vars["name"] = name
        if context:
            template_vars["context"] = context

        _collect_missing_inputs(prompt, template_vars, use_placeholders=True)

        rendered = prompt.render(template_vars)
        input_tokens = estimate_tokens(rendered)
        estimated_cost = estimate_cost(input_tokens, output_tokens, model)

        console.print(f"[bold]Cost Estimation for {model}[/bold]")
        console.print(f"Input tokens: ~{input_tokens}")
        console.print(f"Output tokens: ~{output_tokens}")

        if estimated_cost is not None:
            console.print(f"Estimated cost: {format_cost(estimated_cost)}")
        else:
            console.print(
                f"[yellow]Cost estimation not available for model '{model}'[/yellow]"
            )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def _collect_missing_inputs(
    prompt: Prompt, template_vars: Dict[str, Any], use_placeholders: bool = False
) -> None:
    """Collect missing required inputs interactively or with placeholders."""
    required_inputs = prompt.get_required_inputs()
    missing_inputs = [field for field in required_inputs if field not in template_vars]

    if not missing_inputs:
        return

    if use_placeholders:
        for field in missing_inputs:
            type_str = prompt.input_schema.get(field, "str")
            if "str" in type_str:
                template_vars[field] = f"placeholder_{field}"
            elif "int" in type_str:
                template_vars[field] = 42
            elif "float" in type_str:
                template_vars[field] = 3.14
            elif "bool" in type_str:
                template_vars[field] = True
            else:
                template_vars[field] = f"placeholder_{field}"
        return

    console.print(
        f"[yellow]Missing required inputs: {', '.join(missing_inputs)}[/yellow]"
    )

    for field in missing_inputs:
        type_str = prompt.input_schema.get(field, "str")
        value = typer.prompt(f"Enter value for '{field}' ({type_str})")

        if "int" in type_str:
            try:
                value = int(value)
            except ValueError:
                console.print(
                    f"[yellow]Warning: Could not convert '{value}' to int[/yellow]"
                )
        elif "float" in type_str:
            try:
                value = float(value)
            except ValueError:
                console.print(
                    f"[yellow]Warning: Could not convert '{value}' to float[/yellow]"
                )
        elif "bool" in type_str:
            value = value.lower() in ("true", "yes", "1", "on")

        template_vars[field] = value


if __name__ == "__main__":
    app()
