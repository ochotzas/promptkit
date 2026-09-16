from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel

from promptkit.cache import Cache, make_key
from promptkit.core.prompt import Prompt
from promptkit.core.structured import (
    DEFAULT_PARSE_RETRIES,
    ParsedCompletion,
    parse_output,
    prepare,
    repair_message,
)
from promptkit.engines.base import BaseEngine
from promptkit.errors import OutputValidationError
from promptkit.events import (
    Listener,
    ParseRetried,
    PromptRendered,
    RequestCompleted,
    RequestFailed,
    RequestStarted,
    emit,
)
from promptkit.types import Completion, Message
from promptkit.utils.logging import get_logger

logger = get_logger(__name__)


def _prepare(
    prompt: Prompt,
    inputs: dict[str, Any],
    engine: BaseEngine,
    validate: bool,
    listeners: list[Listener] | None,
) -> list[Message]:
    messages = prompt.render_messages(inputs, validate=validate)

    emit(
        PromptRendered(
            prompt_name=prompt.name,
            model=engine.model,
            characters=sum(len(m.content) for m in messages),
            message_count=len(messages),
        ),
        listeners,
    )

    return messages


def _cache_key(
    prompt: Prompt, messages: list[Message], engine: BaseEngine, options: dict[str, Any]
) -> str:
    return make_key(messages, engine.model, options, namespace=prompt.fingerprint)


def _completed(
    prompt: Prompt,
    engine: BaseEngine,
    completion: Completion,
    started: float,
    cached: bool,
    listeners: list[Listener] | None,
) -> None:
    emit(
        RequestCompleted(
            prompt_name=prompt.name,
            model=completion.model,
            engine=type(engine).__name__,
            usage=completion.usage,
            duration_seconds=time.monotonic() - started,
            cost=engine.cost_of(completion),
            cost_exact=engine.pricing_is_exact(completion),
            cached=cached,
        ),
        listeners,
    )


def _failed(
    prompt: Prompt,
    engine: BaseEngine,
    error: Exception,
    started: float,
    listeners: list[Listener] | None,
) -> None:
    emit(
        RequestFailed(
            prompt_name=prompt.name,
            model=engine.model,
            engine=type(engine).__name__,
            error=str(error),
            error_type=type(error).__name__,
            duration_seconds=time.monotonic() - started,
        ),
        listeners,
    )
    logger.error(f"Failed to run prompt '{prompt.name}': {error}")


def run_prompt(
    prompt: Prompt,
    inputs: dict[str, Any],
    engine: BaseEngine,
    validate_inputs: bool = True,
    cache: Cache | None = None,
    listeners: list[Listener] | None = None,
    **options: Any,
) -> Completion:
    logger.info(f"Running prompt '{prompt.name}' with engine {type(engine).__name__}")
    started = time.monotonic()

    try:
        messages = _prepare(prompt, inputs, engine, validate_inputs, listeners)
        key = _cache_key(prompt, messages, engine, options) if cache is not None else ""

        if cache is not None:
            hit = cache.get(key)

            if hit is not None:
                _completed(prompt, engine, hit, started, True, listeners)

                return hit

        emit(
            RequestStarted(
                prompt_name=prompt.name,
                model=engine.model,
                engine=type(engine).__name__,
            ),
            listeners,
        )
        completion = engine.complete(messages, **options)
    except Exception as e:
        _failed(prompt, engine, e, started, listeners)
        raise

    if cache is not None:
        cache.set(key, completion)

    _completed(prompt, engine, completion, started, False, listeners)

    return completion


async def run_prompt_async(
    prompt: Prompt,
    inputs: dict[str, Any],
    engine: BaseEngine,
    validate_inputs: bool = True,
    cache: Cache | None = None,
    listeners: list[Listener] | None = None,
    **options: Any,
) -> Completion:
    logger.info(
        f"Running prompt '{prompt.name}' async with engine {type(engine).__name__}"
    )
    started = time.monotonic()

    try:
        messages = _prepare(prompt, inputs, engine, validate_inputs, listeners)
        key = _cache_key(prompt, messages, engine, options) if cache is not None else ""

        if cache is not None:
            hit = cache.get(key)

            if hit is not None:
                _completed(prompt, engine, hit, started, True, listeners)

                return hit

        emit(
            RequestStarted(
                prompt_name=prompt.name,
                model=engine.model,
                engine=type(engine).__name__,
            ),
            listeners,
        )
        completion = await engine.acomplete(messages, **options)
    except Exception as e:
        _failed(prompt, engine, e, started, listeners)
        raise

    if cache is not None:
        cache.set(key, completion)

    _completed(prompt, engine, completion, started, False, listeners)

    return completion


def run_prompt_text(
    prompt: Prompt,
    inputs: dict[str, Any],
    engine: BaseEngine,
    validate_inputs: bool = True,
    **options: Any,
) -> str:
    return run_prompt(prompt, inputs, engine, validate_inputs, **options).text


async def run_prompt_text_async(
    prompt: Prompt,
    inputs: dict[str, Any],
    engine: BaseEngine,
    validate_inputs: bool = True,
    **options: Any,
) -> str:
    completion = await run_prompt_async(
        prompt, inputs, engine, validate_inputs, **options
    )

    return completion.text


def _resolve_output_model(
    prompt: Prompt, output_model: type[BaseModel] | None
) -> type[BaseModel] | None:
    return output_model if output_model is not None else prompt.output_model()


def run_structured(
    prompt: Prompt,
    inputs: dict[str, Any],
    engine: BaseEngine,
    output_model: type[BaseModel] | None = None,
    validate_inputs: bool = True,
    max_parse_retries: int = DEFAULT_PARSE_RETRIES,
    listeners: list[Listener] | None = None,
    **options: Any,
) -> ParsedCompletion[Any]:
    model = _resolve_output_model(prompt, output_model)

    if model is None:
        raise OutputValidationError(
            f"prompt '{prompt.name}' has no output_schema and no output_model was given"
        )

    base = prompt.render_messages(inputs, validate=validate_inputs)
    messages, extra = prepare(base, model, engine.capabilities.json_mode)
    attempt = 1

    while True:
        completion = engine.complete(messages, **{**extra, **options})

        try:
            return ParsedCompletion(parse_output(completion.text, model), completion)
        except OutputValidationError as error:
            if attempt > max_parse_retries:
                raise

            emit(
                ParseRetried(
                    prompt_name=prompt.name,
                    model=engine.model,
                    attempt=attempt,
                    error=str(error),
                ),
                listeners,
            )
            messages = [*messages, *repair_message(error, completion.text)]
            attempt += 1


async def run_structured_async(
    prompt: Prompt,
    inputs: dict[str, Any],
    engine: BaseEngine,
    output_model: type[BaseModel] | None = None,
    validate_inputs: bool = True,
    max_parse_retries: int = DEFAULT_PARSE_RETRIES,
    listeners: list[Listener] | None = None,
    **options: Any,
) -> ParsedCompletion[Any]:
    model = _resolve_output_model(prompt, output_model)

    if model is None:
        raise OutputValidationError(
            f"prompt '{prompt.name}' has no output_schema and no output_model was given"
        )

    base = prompt.render_messages(inputs, validate=validate_inputs)
    messages, extra = prepare(base, model, engine.capabilities.json_mode)
    attempt = 1

    while True:
        completion = await engine.acomplete(messages, **{**extra, **options})

        try:
            return ParsedCompletion(parse_output(completion.text, model), completion)
        except OutputValidationError as error:
            if attempt > max_parse_retries:
                raise

            emit(
                ParseRetried(
                    prompt_name=prompt.name,
                    model=engine.model,
                    attempt=attempt,
                    error=str(error),
                ),
                listeners,
            )
            messages = [*messages, *repair_message(error, completion.text)]
            attempt += 1
