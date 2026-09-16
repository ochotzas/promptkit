from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

__version__ = "1.0.0"
__author__ = "Olger Chotza"

_EXPORTS: dict[str, tuple[str, str]] = {
    "AnthropicEngine": ("promptkit.engines.anthropic", "AnthropicEngine"),
    "BaseEngine": ("promptkit.engines.base", "BaseEngine"),
    "Cache": ("promptkit.cache", "Cache"),
    "Capabilities": ("promptkit.types", "Capabilities"),
    "Chunk": ("promptkit.types", "Chunk"),
    "CompatibleEngine": ("promptkit.engines.compatible", "CompatibleEngine"),
    "Completion": ("promptkit.types", "Completion"),
    "DiskCache": ("promptkit.cache", "DiskCache"),
    "EngineError": ("promptkit.errors", "EngineError"),
    "EngineNotFoundError": ("promptkit.errors", "EngineNotFoundError"),
    "EvalCase": ("promptkit.evals", "EvalCase"),
    "EvalSuite": ("promptkit.evals", "EvalSuite"),
    "Finding": ("promptkit.core.lint", "Finding"),
    "InputValidationError": ("promptkit.errors", "InputValidationError"),
    "MemoryCache": ("promptkit.cache", "MemoryCache"),
    "Message": ("promptkit.types", "Message"),
    "MessageTemplate": ("promptkit.core.message", "MessageTemplate"),
    "OllamaEngine": ("promptkit.engines.ollama", "OllamaEngine"),
    "OpenAIEngine": ("promptkit.engines.openai", "OpenAIEngine"),
    "OutputValidationError": ("promptkit.errors", "OutputValidationError"),
    "ParsedCompletion": ("promptkit.core.structured", "ParsedCompletion"),
    "Prompt": ("promptkit.core.prompt", "Prompt"),
    "PromptKitError": ("promptkit.errors", "PromptKitError"),
    "PromptMetadata": ("promptkit.core.prompt", "PromptMetadata"),
    "PromptNotFoundError": ("promptkit.errors", "PromptNotFoundError"),
    "PromptParseError": ("promptkit.errors", "PromptParseError"),
    "PromptRegistry": ("promptkit.core.registry", "PromptRegistry"),
    "RateLimitError": ("promptkit.errors", "RateLimitError"),
    "RetryPolicy": ("promptkit.retry", "RetryPolicy"),
    "Role": ("promptkit.types", "Role"),
    "SchemaError": ("promptkit.errors", "SchemaError"),
    "SuiteResult": ("promptkit.evals", "SuiteResult"),
    "TemplateError": ("promptkit.errors", "TemplateError"),
    "Usage": ("promptkit.types", "Usage"),
    "discover_engines": ("promptkit.engines.plugins", "discover"),
    "lint_prompt": ("promptkit.core.lint", "lint_prompt"),
    "load_engine": ("promptkit.engines.plugins", "load"),
    "load_prompt": ("promptkit.core.loader", "load_prompt"),
    "loads_prompt": ("promptkit.core.loader", "loads_prompt"),
    "run_prompt": ("promptkit.core.runner", "run_prompt"),
    "run_prompt_async": ("promptkit.core.runner", "run_prompt_async"),
    "run_prompt_text": ("promptkit.core.runner", "run_prompt_text"),
    "run_prompt_text_async": ("promptkit.core.runner", "run_prompt_text_async"),
    "run_structured": ("promptkit.core.runner", "run_structured"),
    "run_structured_async": ("promptkit.core.runner", "run_structured_async"),
    "run_suite": ("promptkit.evals", "run_suite"),
    "save_prompt": ("promptkit.core.loader", "save_prompt"),
    "subscribe": ("promptkit.events", "subscribe"),
    "unsubscribe": ("promptkit.events", "unsubscribe"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)

    if target is None:
        raise AttributeError(f"module 'promptkit' has no attribute {name!r}")

    module, attribute = target
    value = getattr(importlib.import_module(module), attribute)
    globals()[name] = value

    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS))


if TYPE_CHECKING:
    from promptkit.cache import Cache, DiskCache, MemoryCache
    from promptkit.core.lint import Finding, lint_prompt
    from promptkit.core.loader import load_prompt, loads_prompt, save_prompt
    from promptkit.core.message import MessageTemplate
    from promptkit.core.prompt import Prompt, PromptMetadata
    from promptkit.core.registry import PromptRegistry
    from promptkit.core.runner import (
        run_prompt,
        run_prompt_async,
        run_prompt_text,
        run_prompt_text_async,
        run_structured,
        run_structured_async,
    )
    from promptkit.core.structured import ParsedCompletion
    from promptkit.engines.anthropic import AnthropicEngine
    from promptkit.engines.base import BaseEngine
    from promptkit.engines.compatible import CompatibleEngine
    from promptkit.engines.ollama import OllamaEngine
    from promptkit.engines.openai import OpenAIEngine
    from promptkit.engines.plugins import discover as discover_engines
    from promptkit.engines.plugins import load as load_engine
    from promptkit.errors import (
        EngineError,
        EngineNotFoundError,
        InputValidationError,
        OutputValidationError,
        PromptKitError,
        PromptNotFoundError,
        PromptParseError,
        RateLimitError,
        SchemaError,
        TemplateError,
    )
    from promptkit.evals import EvalCase, EvalSuite, SuiteResult, run_suite
    from promptkit.events import subscribe, unsubscribe
    from promptkit.retry import RetryPolicy
    from promptkit.types import Capabilities, Chunk, Completion, Message, Role, Usage

__all__ = [
    "AnthropicEngine",
    "BaseEngine",
    "Cache",
    "Capabilities",
    "Chunk",
    "CompatibleEngine",
    "Completion",
    "DiskCache",
    "EngineError",
    "EngineNotFoundError",
    "EvalCase",
    "EvalSuite",
    "Finding",
    "InputValidationError",
    "MemoryCache",
    "Message",
    "MessageTemplate",
    "OllamaEngine",
    "OpenAIEngine",
    "OutputValidationError",
    "ParsedCompletion",
    "Prompt",
    "PromptKitError",
    "PromptMetadata",
    "PromptNotFoundError",
    "PromptParseError",
    "PromptRegistry",
    "RateLimitError",
    "RetryPolicy",
    "Role",
    "SchemaError",
    "SuiteResult",
    "TemplateError",
    "Usage",
    "discover_engines",
    "lint_prompt",
    "load_engine",
    "load_prompt",
    "loads_prompt",
    "run_prompt",
    "run_prompt_async",
    "run_prompt_text",
    "run_prompt_text_async",
    "run_structured",
    "run_structured_async",
    "run_suite",
    "save_prompt",
    "subscribe",
    "unsubscribe",
]
