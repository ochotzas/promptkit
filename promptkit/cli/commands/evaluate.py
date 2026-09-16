from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from promptkit.cli.commands.run import build_engine
from promptkit.cli.shared import PromptArg, console, fail, registry_for
from promptkit.core.loader import load_prompt
from promptkit.core.prompt import Prompt
from promptkit.engines.base import BaseEngine
from promptkit.errors import EvalError, PromptKitError
from promptkit.evals.case import EvalSuite, suite_path_for
from promptkit.evals.cassette import Cassette, CassetteEngine, Mode, cassette_path_for
from promptkit.evals.report import to_json, to_junit, to_terminal
from promptkit.evals.runner import DEFAULT_CONCURRENCY, run_suite, suite_for
from promptkit.types import Completion, Message

EPILOG = (
    "Examples:\n\n"
    "promptkit test greet.yaml\n\n"
    "promptkit test prompts/ --engine ollama --model llama3\n\n"
    "promptkit test greet.yaml --format junit --output results.xml"
)


def run_evals(
    target: PromptArg,
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
    ] = 0.0,
    concurrency: Annotated[
        int, typer.Option("--concurrency", "-j", help="Cases to run at once")
    ] = DEFAULT_CONCURRENCY,
    output_format: Annotated[
        str, typer.Option("--format", help="Output format: text, json or junit")
    ] = "text",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write the report to a file")
    ] = None,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show passing assertions too")
    ] = False,
    record: Annotated[
        bool,
        typer.Option("--record", help="Call the provider and record the responses"),
    ] = False,
    no_cassette: Annotated[
        bool, typer.Option("--no-cassette", help="Always call the provider live")
    ] = False,
    cassette_file: Annotated[
        Path | None,
        typer.Option("--cassette", help="Cassette file to record to or replay from"),
    ] = None,
) -> None:
    try:
        pairs = _targets(target)
    except PromptKitError as e:
        raise fail(e) from e

    if not pairs:
        console.print(f"[yellow]No eval suites found for {target}[/yellow]")
        console.print(
            f"[dim]Expected a file named like {suite_path_for(target).name}[/dim]"
        )

        raise typer.Exit(1)

    mode: Mode = "off" if no_cassette else ("record" if record else "auto")
    failed = False
    rendered: list[str] = []
    llm: BaseEngine = (
        LazyEngine(engine, model, api_key, temperature)
        if mode != "off"
        else build_engine(engine, model, api_key, temperature, None)
    )
    cassettes: list[Cassette] = []

    try:
        for prompt, suite in pairs:
            runner_engine = llm

            if mode != "off":
                path = cassette_file or cassette_path_for(_suite_path(target, prompt))
                cassette = Cassette.load(path)
                cassettes.append(cassette)
                runner_engine = CassetteEngine(llm, cassette, mode)

            result = run_suite(prompt, suite, runner_engine, concurrency=concurrency)
            failed = failed or not result.ok

            if output_format == "json":
                rendered.append(to_json(result))
            elif output_format == "junit":
                rendered.append(to_junit(result))
            else:
                to_terminal(result, console, verbose)
    except (EvalError, PromptKitError) as e:
        raise fail(e) from e
    finally:
        for cassette in cassettes:
            cassette.save()

        llm.close()

    if mode == "record" and cassettes:
        total = sum(len(c) for c in cassettes)
        console.print(f"[dim]recorded {total} response(s) to cassette[/dim]")

    if rendered:
        text = "\n".join(rendered)

        if output is not None:
            output.write_text(text, encoding="utf-8")
            console.print(f"Report written to {output}")
        else:
            console.print(text, highlight=False)

    if failed:
        raise typer.Exit(1)


def _targets(target: Path) -> list[tuple[Prompt, EvalSuite]]:
    if target.is_dir():
        registry = registry_for(target)
        found: list[tuple[Prompt, EvalSuite]] = []

        for name in registry.names():
            prompt = registry.get(name)
            suite = suite_for(registry.resolve(name))

            if suite is not None and len(suite):
                found.append((prompt, suite))

        return found

    suite = suite_for(target)

    if suite is None or not len(suite):
        return []

    return [(load_prompt(target), suite)]


def register(app: typer.Typer) -> None:
    app.command(
        name="test",
        help="Run the eval suites for a prompt or directory.",
        epilog=EPILOG,
    )(run_evals)


class LazyEngine(BaseEngine):
    def __init__(
        self,
        engine: str,
        model: str | None,
        api_key: str | None,
        temperature: float,
    ) -> None:
        super().__init__(model or "lazy")
        self._spec = (engine, model, api_key, temperature)
        self._built: BaseEngine | None = None

    @property
    def inner(self) -> BaseEngine:
        if self._built is None:
            engine, model, api_key, temperature = self._spec
            self._built = build_engine(engine, model, api_key, temperature, None)
            self.model = self._built.model

        return self._built

    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        return self.inner.complete(messages, **options)

    async def _acomplete(self, messages: list[Message], **options: Any) -> Completion:
        return await self.inner.acomplete(messages, **options)

    def close(self) -> None:
        if self._built is not None:
            self._built.close()
            self._built = None


def _suite_path(target: Path, prompt: Any) -> Path:
    if target.is_dir():
        return target / f"{prompt.name}.evals.yaml"

    return target
