from __future__ import annotations

from typing import Any

import yaml
from jinja2 import TemplateError as JinjaTemplateError
from pydantic import ValidationError as PydanticValidationError


class PromptKitError(Exception):
    pass


class PromptError(PromptKitError):
    pass


class PromptNotFoundError(PromptError, FileNotFoundError):
    def __init__(self, path: str, message: str | None = None) -> None:
        self.path = path
        super().__init__(message or f"Prompt file not found: {path}")


class PromptParseError(PromptError, yaml.YAMLError, ValueError):
    def __init__(
        self,
        message: str,
        path: str | None = None,
        missing_fields: list[str] | None = None,
    ) -> None:
        self.path = path
        self.missing_fields = missing_fields or []
        super().__init__(message)


class TemplateError(PromptError, JinjaTemplateError):
    def __init__(self, message: str, template_name: str | None = None) -> None:
        self.template_name = template_name
        super().__init__(message)


class SchemaError(PromptError, ValueError):
    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class ValidationError(PromptKitError, ValueError):
    def __init__(
        self, message: str, cause: PydanticValidationError | None = None
    ) -> None:
        self.cause = cause
        super().__init__(message)

    def errors(self) -> list[Any]:
        return list(self.cause.errors()) if self.cause is not None else []


class InputValidationError(ValidationError):
    pass


class OutputValidationError(ValidationError):
    pass


class EngineError(PromptKitError):
    def __init__(self, message: str, model: str | None = None) -> None:
        self.model = model
        super().__init__(message)


class EngineNotFoundError(EngineError):
    def __init__(self, name: str, install_hint: str | None = None) -> None:
        self.name = name
        self.install_hint = install_hint
        message = f"Unknown engine: {name}"
        if install_hint:
            message = f"{message}. Install it with: {install_hint}"
        super().__init__(message)


class AuthenticationError(EngineError):
    pass


class RateLimitError(EngineError):
    def __init__(
        self,
        message: str,
        model: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, model)


class ModelNotFoundError(EngineError):
    pass


class ContextLengthError(EngineError):
    pass


class ProviderError(EngineError):
    def __init__(
        self,
        message: str,
        model: str | None = None,
        status_code: int | None = None,
        body: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(message, model)


class EvalError(PromptKitError):
    pass


__all__ = [
    "AuthenticationError",
    "ContextLengthError",
    "EngineError",
    "EngineNotFoundError",
    "EvalError",
    "InputValidationError",
    "ModelNotFoundError",
    "OutputValidationError",
    "PromptError",
    "PromptKitError",
    "PromptNotFoundError",
    "PromptParseError",
    "ProviderError",
    "RateLimitError",
    "SchemaError",
    "TemplateError",
    "ValidationError",
]
