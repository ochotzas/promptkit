from __future__ import annotations

import pytest

from promptkit.core.compiler import PromptCompiler, fingerprint
from promptkit.core.prompt import Prompt
from promptkit.errors import TemplateError

ESCAPE_ATTEMPTS = [
    "{{ x.__class__ }}",
    "{{ x.__class__.__mro__ }}",
    "{{ x.__init__.__globals__ }}",
    "{{ ''.__class__.__mro__[1].__subclasses__() }}",
    "{{ x.__getattribute__('__class__') }}",
    "{{ self.__init__.__globals__.os }}",
    "{{ cycler.__init__.__globals__.os.popen('id').read() }}",
]


class TestSandbox:
    @pytest.mark.parametrize("source", ESCAPE_ATTEMPTS)
    def test_escape_attempt_is_blocked(self, source: str) -> None:
        compiler = PromptCompiler()

        with pytest.raises(TemplateError):
            compiler.render_string(source, {"x": 1})

    def test_ordinary_templates_still_render(self) -> None:
        compiler = PromptCompiler()
        source = "{% for i in items %}{{ i|upper }} {% endfor %}"

        assert compiler.render_string(source, {"items": ["a", "b"]}) == "A B "

    def test_strict_undefined_is_kept(self) -> None:
        compiler = PromptCompiler()

        with pytest.raises(TemplateError):
            compiler.render_string("{{ missing }}", {})

    def test_prompt_render_is_sandboxed(self) -> None:
        prompt = Prompt(name="n", description="d", template="{{ x.__class__ }}")

        with pytest.raises(TemplateError):
            prompt.render({"x": 1}, validate=False)


class TestTemplateCache:
    def test_same_template_compiles_once(self) -> None:
        compiler = PromptCompiler()

        for _ in range(5):
            compiler.render_string("Hi {{ n }}", {"n": "A"})

        assert compiler.cache_size_now() == 1

    def test_distinct_templates_cached_separately(self) -> None:
        compiler = PromptCompiler()
        compiler.render_string("A {{ n }}", {"n": 1})
        compiler.render_string("B {{ n }}", {"n": 1})

        assert compiler.cache_size_now() == 2

    def test_cache_is_bounded(self) -> None:
        compiler = PromptCompiler(cache_size=3)

        for i in range(10):
            compiler.render_string(f"T{i} {{{{ n }}}}", {"n": 1})

        assert compiler.cache_size_now() == 3

    def test_clear_cache(self) -> None:
        compiler = PromptCompiler()
        compiler.render_string("Hi", {})
        compiler.clear_cache()

        assert compiler.cache_size_now() == 0

    def test_fingerprint_is_stable_and_distinct(self) -> None:
        assert fingerprint("a") == fingerprint("a")
        assert fingerprint("a") != fingerprint("b")

    def test_compilation_error_is_not_cached(self) -> None:
        compiler = PromptCompiler()

        with pytest.raises(TemplateError):
            compiler.compile_template("{% for %}")

        assert compiler.cache_size_now() == 0
