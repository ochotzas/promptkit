from __future__ import annotations

from typing import Annotated, Any

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
from promptkit.core.runner import run_prompt, run_structured
from promptkit.engines import plugins
from promptkit.errors import PromptKitError
from promptkit.pricing import format_cost
from promptkit.utils.logging import configure_logging

EPILOG = (
    "Examples:\n\n"
    "promptkit run greet.yaml --set name=Alice\n\n"
    "promptkit run greet.yaml --engine ollama --model llama3 --stream\n\n"
    "promptkit run invoice.yaml --set document=@- --structured"
)


def build_engine(
    name: str,
    model: str | None,
    api_key: str | None,
    temperature: float | None,
    max_tokens: int | None,
) -> Any:
    engine_class = plugins.load(name.lower())
    kwargs: dict[str, Any] = {"temperature": temperature, "max_tokens": max_tokens}

    if model is not None:
        kwargs["model"] = model

    accepted = engine_class.__init__.__code__.co_varnames

    if "api_key" in accepted and api_key is not None:
        kwargs["api_key"] = api_key

    return engine_class(**kwargs)


def run(
    prompt_file: PromptArg,
    engine: Annotated[
        str, typer.Option("--engine", "-e", help="Engine name")
    ] = "openai",
    model: Annotated[
        str | None, typer.Option("--model", "-m", help="Model name")
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option("--key", "-k", help="API key", envvar="OPENAI_API_KEY"),
    ] = None,
    temperature: Annotated[
        float, typer.Option("--temperature", "-t", help="Sampling temperature")
    ] = 0.7,
    max_tokens: Annotated[
        int | None, typer.Option("--max-tokens", help="Maximum tokens to generate")
    ] = None,
    set_pairs: SetOpt = None,
    variables: VarsOpt = None,
    vars_file: VarsFileOpt = None,
    stream: Annotated[
        bool, typer.Option("--stream", help="Stream the response as it arrives")
    ] = False,
    structured: Annotated[
        bool,
        typer.Option("--structured", help="Parse the response against output_schema"),
    ] = False,
    interactive: Annotated[
        bool, typer.Option("--interactive", "-i", help="Prompt for missing variables")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Verbose logging")
    ] = False,
) -> None:
    if verbose:
        configure_logging("DEBUG")

    prompt = open_prompt(prompt_file, verbose)

    try:
        values = cli_vars.collect(
            prompt,
            console,
            set_pairs,
            variables,
            vars_file,
            interactive,
        )
        llm = build_engine(engine, model, api_key, temperature, max_tokens)
    except PromptKitError as e:
        raise fail(e, verbose) from e

    try:
        if stream:
            _stream(prompt, values, llm)

            return

        if structured:
            parsed = run_structured(prompt, values, llm)
            console.print_json(parsed.value.model_dump_json())
            _report(llm, parsed.completion)

            return

        completion = run_prompt(prompt, values, llm)
        console.print(completion.text)
        _report(llm, completion)
    except PromptKitError as e:
        raise fail(e, verbose) from e
    finally:
        llm.close()


def _stream(prompt: Any, values: dict[str, Any], llm: Any) -> None:
    for chunk in llm.stream(prompt.render_messages(values)):
        console.print(chunk.text, end="")

    console.print()


def _report(llm: Any, completion: Any) -> None:
    usage = completion.usage
    label = "estimated" if usage.estimated else "actual"
    cost = llm.cost_of(completion)
    line = f"[dim]{label}: {usage.prompt_tokens} in, {usage.completion_tokens} out"

    if cost is not None:
        line = f"{line} | {format_cost(cost)}"

    console.print(f"{line}[/dim]")


def register(app: typer.Typer) -> None:
    app.command(help="Run a prompt against an engine.", epilog=EPILOG)(run)
