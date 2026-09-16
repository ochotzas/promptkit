from __future__ import annotations

import hashlib
from typing import Any

from jinja2 import BaseLoader, StrictUndefined, Template
from jinja2 import TemplateError as JinjaTemplateError
from jinja2.sandbox import SandboxedEnvironment

from promptkit.errors import TemplateError

MAX_CACHE_ENTRIES = 512


def fingerprint(template_str: str) -> str:
    return hashlib.sha256(template_str.encode("utf-8")).hexdigest()


class PromptCompiler:
    def __init__(
        self,
        cache_size: int = MAX_CACHE_ENTRIES,
        loader: BaseLoader | None = None,
    ) -> None:
        self.env = SandboxedEnvironment(
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,
            loader=loader,
        )
        self.cache_size = cache_size
        self._cache: dict[str, Template] = {}

    def compile_template(self, template_str: str) -> Template:
        key = fingerprint(template_str)
        cached = self._cache.get(key)

        if cached is not None:
            return cached

        try:
            template = self.env.from_string(template_str)
        except JinjaTemplateError as e:
            raise TemplateError(f"Template compilation failed: {e}") from e

        if len(self._cache) >= self.cache_size:
            self._cache.pop(next(iter(self._cache)), None)

        self._cache[key] = template

        return template

    def render_template(self, template: Template, variables: dict[str, Any]) -> str:
        try:
            return template.render(**variables)
        except JinjaTemplateError as e:
            raise TemplateError(
                f"Template rendering failed: {e}", template_name=template.name
            ) from e

    def render_string(self, template_str: str, variables: dict[str, Any]) -> str:
        return self.render_template(self.compile_template(template_str), variables)

    def clear_cache(self) -> None:
        self._cache.clear()

    def cache_size_now(self) -> int:
        return len(self._cache)


default_compiler = PromptCompiler()

_by_root: dict[str, PromptCompiler] = {}


def compiler_for(root: str | None) -> PromptCompiler:
    if root is None:
        return default_compiler

    cached = _by_root.get(root)

    if cached is None:
        from promptkit.core.template import ConfinedLoader

        cached = PromptCompiler(loader=ConfinedLoader(root))
        _by_root[root] = cached

    return cached


def clear_compilers() -> None:
    _by_root.clear()
    default_compiler.clear_cache()
