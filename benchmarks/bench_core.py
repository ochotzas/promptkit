from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from promptkit.core.compiler import PromptCompiler
from promptkit.core.loader import loads_prompt
from promptkit.core.prompt import Prompt
from promptkit.core.registry import PromptRegistry

SIMPLE = (
    "name: p{i}\ndescription: d\n"
    "template: Hello {{{{ name }}}}\ninput_schema: {{name: str}}\n"
)

LOOP_TEMPLATE = """
Summarise these items for {{ audience }}:
{% for item in items %}
- {{ item.title }} ({{ item.count }})
{% endfor %}
{% if note %}Note: {{ note }}{% endif %}
"""


@pytest.fixture(scope="module")
def simple_prompt() -> Prompt:
    return Prompt(
        name="greet",
        description="d",
        template="Hello {{ name }}",
        input_schema={"name": "str"},
    )


@pytest.fixture(scope="module")
def loop_prompt() -> Prompt:
    return Prompt(
        name="summary",
        description="d",
        template=LOOP_TEMPLATE,
        input_schema={"audience": "str", "items": "list", "note": "str | None"},
    )


@pytest.fixture(scope="module")
def loop_inputs() -> dict[str, Any]:
    return {
        "audience": "engineers",
        "items": [{"title": f"Item {i}", "count": i} for i in range(50)],
        "note": "handle with care",
    }


@pytest.fixture
def tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("prompts")

    for i in range(100):
        (root / f"p{i}.yaml").write_text(SIMPLE.format(i=i))

    return root


def test_render_simple(benchmark: Any, simple_prompt: Prompt) -> None:
    benchmark(simple_prompt.render, {"name": "Alice"})


def test_render_simple_without_validation(
    benchmark: Any, simple_prompt: Prompt
) -> None:
    benchmark(simple_prompt.render, {"name": "Alice"}, validate=False)


def test_render_with_loop(
    benchmark: Any, loop_prompt: Prompt, loop_inputs: dict[str, Any]
) -> None:
    benchmark(loop_prompt.render, loop_inputs)


def test_render_messages(benchmark: Any, simple_prompt: Prompt) -> None:
    benchmark(simple_prompt.render_messages, {"name": "Alice"})


def test_fingerprint(benchmark: Any, loop_prompt: Prompt) -> None:
    benchmark(lambda: loop_prompt.fingerprint)


def test_validate_inputs(benchmark: Any, simple_prompt: Prompt) -> None:
    benchmark(simple_prompt.validate_inputs, {"name": "Alice"})


def test_parse_prompt_yaml(benchmark: Any) -> None:
    text = SIMPLE.format(i=0)
    benchmark(loads_prompt, text)


def test_compile_uncached(benchmark: Any) -> None:
    def compile_fresh() -> None:
        PromptCompiler().compile_template(LOOP_TEMPLATE)

    benchmark(compile_fresh)


def test_compile_cached(benchmark: Any) -> None:
    compiler = PromptCompiler()
    compiler.compile_template(LOOP_TEMPLATE)
    benchmark(compiler.compile_template, LOOP_TEMPLATE)


def test_registry_cold_load(benchmark: Any, tree: Path) -> None:
    def load_all() -> None:
        PromptRegistry(tree).all()

    benchmark(load_all)


def test_registry_warm_load(benchmark: Any, tree: Path) -> None:
    registry = PromptRegistry(tree)
    registry.all()
    benchmark(registry.all)


def test_registry_discovery(benchmark: Any, tree: Path) -> None:
    benchmark(PromptRegistry(tree).names)
