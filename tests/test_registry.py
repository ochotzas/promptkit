from __future__ import annotations

import re
from pathlib import Path

import pytest

from promptkit.core.registry import PromptRegistry, to_identifier
from promptkit.errors import PromptNotFoundError
from tests.conftest import bump_mtime

SIMPLE = (
    "name: {name}\ndescription: d\ntemplate: Hi {{{{ n }}}}\ninput_schema: {{n: str}}\n"
)


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "greet.yaml").write_text(SIMPLE.format(name="greet"))
    (tmp_path / "support").mkdir()
    (tmp_path / "support" / "refund.yaml").write_text(SIMPLE.format(name="refund"))
    (tmp_path / "support" / "escalate.yml").write_text(SIMPLE.format(name="escalate"))
    (tmp_path / "_partials").mkdir()
    (tmp_path / "_partials" / "tone.j2").write_text("Be kind.")
    (tmp_path / "_partials" / "draft.yaml").write_text(SIMPLE.format(name="draft"))

    return tmp_path


class TestDiscovery:
    def test_dotted_namespaces(self, tree: Path) -> None:
        assert PromptRegistry(tree).names() == [
            "greet",
            "support.escalate",
            "support.refund",
        ]

    def test_partial_directories_are_excluded(self, tree: Path) -> None:
        assert "_partials.draft" not in PromptRegistry(tree).names()

    def test_partials_are_listed_separately(self, tree: Path) -> None:
        partials = PromptRegistry(tree).partials()

        assert "_partials/tone.j2" in partials

    def test_both_yaml_suffixes_are_found(self, tree: Path) -> None:
        assert "support.escalate" in PromptRegistry(tree)

    def test_missing_root_is_empty(self, tmp_path: Path) -> None:
        registry = PromptRegistry(tmp_path / "nope")

        assert registry.names() == []
        assert len(registry) == 0

    def test_identifier_conversion(self, tree: Path) -> None:
        path = tree / "support" / "refund.yaml"

        assert to_identifier(tree, path) == "support.refund"


class TestAccess:
    def test_get_loads_a_prompt(self, tree: Path) -> None:
        assert PromptRegistry(tree).get("support.refund").name == "refund"

    def test_getitem(self, tree: Path) -> None:
        assert PromptRegistry(tree)["greet"].name == "greet"

    def test_unknown_name_raises(self, tree: Path) -> None:
        with pytest.raises(PromptNotFoundError, match=re.escape("support.nope")):
            PromptRegistry(tree).get("support.nope")

    def test_contains_and_len(self, tree: Path) -> None:
        registry = PromptRegistry(tree)

        assert "greet" in registry
        assert "nope" not in registry
        assert len(registry) == 3

    def test_iteration(self, tree: Path) -> None:
        assert list(PromptRegistry(tree)) == PromptRegistry(tree).names()

    def test_all_returns_every_prompt(self, tree: Path) -> None:
        assert set(PromptRegistry(tree).all()) == set(PromptRegistry(tree).names())

    def test_repr_is_informative(self, tree: Path) -> None:
        assert "prompts=3" in repr(PromptRegistry(tree))


class TestCaching:
    def test_repeat_access_returns_the_same_object(self, tree: Path) -> None:
        registry = PromptRegistry(tree)

        assert registry.get("greet") is registry.get("greet")

    def test_edit_invalidates_the_cache(self, tree: Path) -> None:
        registry = PromptRegistry(tree)
        before = registry.get("greet")
        (tree / "greet.yaml").write_text(
            "name: greet\ndescription: changed\n"
            "template: Bye {{ n }}\ninput_schema: {n: str}\n"
        )
        bump_mtime(tree / "greet.yaml")
        after = registry.get("greet")

        assert after is not before
        assert after.description == "changed"

    def test_clear_cache(self, tree: Path) -> None:
        registry = PromptRegistry(tree)
        first = registry.get("greet")
        registry.clear_cache()

        assert registry.get("greet") is not first


class TestEvalSuites:
    def test_eval_suites_are_not_prompts(self, tree: Path) -> None:
        (tree / "greet.evals.yaml").write_text("cases: []\n")

        assert "greet.evals" not in PromptRegistry(tree).names()

    def test_eval_suite_next_to_a_prompt_does_not_break_listing(
        self, tree: Path
    ) -> None:
        (tree / "support" / "refund.evals.yaml").write_text("cases: []\n")
        registry = PromptRegistry(tree)

        assert registry.names() == ["greet", "support.escalate", "support.refund"]


class TestComposition:
    def test_registry_roots_the_template_loader(self, tmp_path: Path) -> None:
        (tmp_path / "_partials").mkdir()
        (tmp_path / "_partials" / "tone.j2").write_text("Be kind.")
        (tmp_path / "deep").mkdir()
        (tmp_path / "deep" / "child.yaml").write_text(
            "name: child\ndescription: d\n"
            "messages:\n"
            "  - role: system\n"
            "    template: \"{% include '_partials/tone.j2' %}\"\n"
            "  - role: user\n"
            "    template: Hi\n"
        )
        prompt = PromptRegistry(tmp_path).get("deep.child")

        assert prompt.render_messages({})[0].content == "Be kind."


class TestPathCaching:
    def test_listing_is_cached(self, tree: Path) -> None:
        registry = PromptRegistry(tree)

        assert registry.paths() is registry.paths()

    def test_refresh_rescans(self, tree: Path) -> None:
        registry = PromptRegistry(tree)
        registry.names()
        (tree / "added.yaml").write_text(SIMPLE.format(name="added"))

        assert "added" not in registry.paths()
        assert "added" in registry.paths(refresh=True)

    def test_clear_cache_refreshes_the_listing(self, tree: Path) -> None:
        registry = PromptRegistry(tree)
        registry.names()
        (tree / "added.yaml").write_text(SIMPLE.format(name="added"))
        registry.clear_cache()

        assert "added" in registry.names()

    def test_get_finds_a_file_added_after_the_first_scan(self, tree: Path) -> None:
        registry = PromptRegistry(tree)
        registry.names()
        (tree / "added.yaml").write_text(SIMPLE.format(name="added"))

        assert registry.get("added").name == "added"


VERSIONED = (
    "name: refund\ndescription: d\nversion: {version}\n"
    "template: Hi {{{{ n }}}}\ninput_schema: {{n: str}}\n"
)


@pytest.fixture
def versioned(tmp_path: Path) -> Path:
    (tmp_path / "support").mkdir()

    for stem, version in (
        ("refund", "1.0.0"),
        ("refund_v2", "2.1.0"),
        ("refund_v3", "2.10.0"),
    ):
        (tmp_path / "support" / f"{stem}.yaml").write_text(
            VERSIONED.format(version=version)
        )

    return tmp_path


class TestVersionResolution:
    def test_versions_are_discovered(self, versioned: Path) -> None:
        assert set(PromptRegistry(versioned).versions("support.refund")) == {
            "1.0.0",
            "2.1.0",
            "2.10.0",
        }

    def test_pinned_version_resolves(self, versioned: Path) -> None:
        assert PromptRegistry(versioned).get("support.refund@2.1.0").version == "2.1.0"

    def test_latest_resolves_numerically(self, versioned: Path) -> None:
        assert PromptRegistry(versioned).get("refund@latest").version == "2.10.0"

    def test_declared_name_is_enough(self, versioned: Path) -> None:
        assert PromptRegistry(versioned).get("refund@1.0.0").version == "1.0.0"

    def test_bare_identifier_is_unchanged(self, versioned: Path) -> None:
        assert PromptRegistry(versioned).get("support.refund").version == "1.0.0"

    def test_unknown_version_lists_what_exists(self, versioned: Path) -> None:
        with pytest.raises(PromptNotFoundError, match=re.escape("2.10.0")):
            PromptRegistry(versioned).get("refund@9.9.9")

    def test_unknown_name_is_reported(self, versioned: Path) -> None:
        with pytest.raises(PromptNotFoundError):
            PromptRegistry(versioned).get("nope@1.0.0")

    @pytest.mark.parametrize(
        ("identifier", "expected"),
        [
            ("refund", ("refund", None)),
            ("refund@1.0.0", ("refund", "1.0.0")),
            ("support.refund@latest", ("support.refund", "latest")),
        ],
    )
    def test_identifier_splitting(
        self, tmp_path: Path, identifier: str, expected: tuple[str, str | None]
    ) -> None:
        assert PromptRegistry(tmp_path).split_version(identifier) == expected
