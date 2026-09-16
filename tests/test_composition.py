from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from promptkit.core.compiler import PromptCompiler, clear_compilers
from promptkit.core.loader import load_prompt
from promptkit.core.template import (
    MAX_INCLUDE_DEPTH,
    ConfinedLoader,
    is_partial,
    resolve_dependencies,
    safe_join,
)
from promptkit.errors import TemplateError

PROMPT_WITH_INCLUDE = """
name: greet
description: greeting with a shared preamble
messages:
  - role: system
    template: "{% include '_partials/tone.j2' %}"
  - role: user
    template: "Hello {{ name }}"
input_schema:
  name: str
"""


@pytest.fixture(autouse=True)
def _fresh_compilers() -> None:
    clear_compilers()


@pytest.fixture
def registry(tmp_path: Path) -> Path:
    (tmp_path / "_partials").mkdir()
    (tmp_path / "_partials" / "tone.j2").write_text("Always be concise.")
    (tmp_path / "greet.yaml").write_text(PROMPT_WITH_INCLUDE)

    return tmp_path


class TestConfinement:
    @pytest.mark.parametrize(
        "name",
        [
            "/etc/passwd",
            "//etc/passwd",
            "../secret.j2",
            "../../etc/passwd",
            "_partials/../../escape.j2",
            "..",
            "./..",
            "a/../../b",
            "\\\\server\\share",
            "..\\..\\windows",
            "C:/windows/system32",
            "",
            "\x00evil",
        ],
    )
    def test_path_is_rejected(self, tmp_path: Path, name: str) -> None:
        with pytest.raises(TemplateError):
            safe_join(tmp_path, name)

    def test_ordinary_relative_path_is_allowed(self, tmp_path: Path) -> None:
        resolved = safe_join(tmp_path, "_partials/tone.j2")

        assert resolved.parent.name == "_partials"

    def test_nested_relative_path_is_allowed(self, tmp_path: Path) -> None:
        assert safe_join(tmp_path, "a/b/c.j2").name == "c.j2"

    def test_dot_segments_inside_root_are_normalised(self, tmp_path: Path) -> None:
        assert safe_join(tmp_path, "a/./b/../c.j2").name == "c.j2"

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlinks")
    def test_symlink_escaping_root_is_rejected(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / "outside_secret"
        outside.mkdir(exist_ok=True)
        (outside / "secret.j2").write_text("TOP SECRET")

        root = tmp_path / "root"
        root.mkdir()
        (root / "leak.j2").symlink_to(outside / "secret.j2")

        with pytest.raises(TemplateError, match="escapes the template root"):
            safe_join(root, "leak.j2")

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlinks")
    def test_symlinked_directory_escaping_root_is_rejected(
        self, tmp_path: Path
    ) -> None:
        outside = tmp_path.parent / "outside_dir"
        outside.mkdir(exist_ok=True)
        (outside / "secret.j2").write_text("TOP SECRET")

        root = tmp_path / "root2"
        root.mkdir()
        (root / "linked").symlink_to(outside, target_is_directory=True)

        with pytest.raises(TemplateError, match="escapes the template root"):
            safe_join(root, "linked/secret.j2")

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlinks")
    def test_symlink_staying_inside_root_is_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "real.j2").write_text("fine")
        (tmp_path / "alias.j2").symlink_to(tmp_path / "real.j2")

        assert safe_join(tmp_path, "alias.j2").exists()

    def test_loader_read_rejects_traversal(self, tmp_path: Path) -> None:
        loader = ConfinedLoader(tmp_path)

        with pytest.raises(TemplateError):
            loader.read("../../etc/passwd")

    def test_loader_read_reports_missing_template(self, tmp_path: Path) -> None:
        with pytest.raises(TemplateError, match="not found"):
            ConfinedLoader(tmp_path).read("nope.j2")

    def test_render_cannot_include_outside_root(self, tmp_path: Path) -> None:
        (tmp_path.parent / "outside.j2").write_text("LEAKED")
        root = tmp_path / "root3"
        root.mkdir()
        compiler = PromptCompiler(loader=ConfinedLoader(root))

        with pytest.raises(TemplateError):
            compiler.render_string("{% include '../outside.j2' %}", {})


class TestDepthLimit:
    def test_cycle_is_caught(self, tmp_path: Path) -> None:
        (tmp_path / "a.j2").write_text("{% include 'b.j2' %}")
        (tmp_path / "b.j2").write_text("{% include 'a.j2' %}")
        loader = ConfinedLoader(tmp_path)
        compiler = PromptCompiler(loader=loader)
        source = "{% include 'a.j2' %}"

        dependencies = resolve_dependencies(compiler.env, [source], loader)

        assert set(dependencies) == {"a.j2", "b.j2"}

    def test_deep_chain_exceeding_limit_is_rejected(self, tmp_path: Path) -> None:
        depth = MAX_INCLUDE_DEPTH + 3

        for i in range(depth):
            nxt = f"{{% include 't{i + 1}.j2' %}}" if i < depth - 1 else "end"
            (tmp_path / f"t{i}.j2").write_text(nxt)

        loader = ConfinedLoader(tmp_path)
        compiler = PromptCompiler(loader=loader)

        with pytest.raises(TemplateError, match="include depth exceeded"):
            resolve_dependencies(compiler.env, ["{% include 't0.j2' %}"], loader)


class TestPartials:
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("_partials/tone.j2", True),
            ("a/_shared/x.j2", True),
            ("_tone.j2", True),
            ("partials/tone.j2", False),
            ("greet.yaml", False),
        ],
    )
    def test_partial_detection(self, path: str, expected: bool) -> None:
        assert is_partial(path) is expected


class TestComposition:
    def test_include_renders(self, registry: Path) -> None:
        prompt = load_prompt(registry / "greet.yaml")
        messages = prompt.render_messages({"name": "Ada"})

        assert messages[0].content == "Always be concise."
        assert messages[1].content == "Hello Ada"

    def test_dependencies_recorded(self, registry: Path) -> None:
        prompt = load_prompt(registry / "greet.yaml")

        assert dict(prompt.dependencies).keys() == {"_partials/tone.j2"}

    def test_editing_a_partial_changes_the_fingerprint(self, registry: Path) -> None:
        before = load_prompt(registry / "greet.yaml").fingerprint
        (registry / "_partials" / "tone.j2").write_text("Always be verbose.")
        after = load_prompt(registry / "greet.yaml").fingerprint

        assert before != after

    def test_editing_a_partial_changes_the_render(self, registry: Path) -> None:
        load_prompt(registry / "greet.yaml").render_messages({"name": "Ada"})
        time.sleep(0.02)
        (registry / "_partials" / "tone.j2").write_text("Always be verbose.")
        clear_compilers()
        rendered = load_prompt(registry / "greet.yaml").render_messages({"name": "Ada"})

        assert rendered[0].content == "Always be verbose."

    def test_missing_partial_is_an_error(self, tmp_path: Path) -> None:
        (tmp_path / "broken.yaml").write_text(
            "name: b\ndescription: d\ntemplate: \"{% include 'missing.j2' %}\"\n"
        )

        with pytest.raises(TemplateError):
            load_prompt(tmp_path / "broken.yaml")

    def test_prompt_without_includes_has_no_dependencies(self, tmp_path: Path) -> None:
        (tmp_path / "plain.yaml").write_text(
            "name: p\ndescription: d\ntemplate: Hello {{ n }}\ninput_schema: {n: str}\n"
        )

        assert load_prompt(tmp_path / "plain.yaml").dependencies == ()

    def test_root_override(self, registry: Path, tmp_path: Path) -> None:
        nested = registry / "nested"
        nested.mkdir()
        (nested / "child.yaml").write_text(PROMPT_WITH_INCLUDE)
        prompt = load_prompt(nested / "child.yaml", root=registry)

        assert (
            prompt.render_messages({"name": "Ada"})[0].content == "Always be concise."
        )
