from __future__ import annotations

from pathlib import Path

import pytest

from promptkit.codemod import apply_rewrites, find_review_items, main, python_files

LEGACY = """from promptkit import load_prompt, run_prompt
from promptkit.engines.ollama import OllamaEngine
from promptkit.utils.tokens import get_model_pricing

prompt = load_prompt("greet.yaml")
print(prompt.template)
rates = get_model_pricing("gpt-4o-mini")
engine = OllamaEngine(model="llama2", base_url="http://localhost:11434")
text = run_prompt(prompt, {"name": "Alice"}, engine)
"""


class TestRewrites:
    @pytest.mark.parametrize(
        "source",
        [
            "print(response.template)",
            "tpl = env.template",
            "report.template.render()",
            'Prompt(name="n", description="d", template="Hi")',
        ],
    )
    def test_template_attribute_is_never_rewritten(self, source: str) -> None:
        result, applied = apply_rewrites(source)

        assert result == source
        assert applied == []

    def test_template_attribute_is_flagged_for_a_human(self) -> None:
        found = find_review_items("print(response.template)")

        assert any("common attribute name" in item for item in found)

    def test_get_model_pricing_import_moves_module(self) -> None:
        result, _ = apply_rewrites(
            "from promptkit.utils.tokens import get_model_pricing"
        )

        assert result == "from promptkit.pricing import get_pricing"

    def test_mixed_import_is_split_correctly(self) -> None:
        result, _ = apply_rewrites(
            "from promptkit.utils.tokens import estimate_tokens, get_model_pricing"
        )

        assert "from promptkit.pricing import get_pricing" in result
        assert "from promptkit.utils.tokens import estimate_tokens" in result
        assert "get_model_pricing" not in result

    def test_unrelated_tokens_import_is_untouched(self) -> None:
        source = "from promptkit.utils.tokens import estimate_tokens"
        result, _ = apply_rewrites(source)

        assert result == source

    def test_ollama_base_url(self) -> None:
        result, _ = apply_rewrites('OllamaEngine(model="m", base_url="http://x")')

        assert "host=" in result
        assert "base_url=" not in result

    def test_other_base_url_is_untouched(self) -> None:
        source = 'OpenAIEngine(base_url="https://x/v1")'
        result, _ = apply_rewrites(source)

        assert result == source

    def test_clean_source_is_unchanged(self) -> None:
        source = "from promptkit import load_prompt\n"
        result, applied = apply_rewrites(source)

        assert result == source
        assert applied == []


class TestReviewItems:
    def test_run_prompt_is_flagged(self) -> None:
        found = find_review_items("text = run_prompt(p, i, e)")

        assert any("Completion" in item for item in found)

    def test_custom_engine_generate_is_flagged(self) -> None:
        found = find_review_items("def generate(self, prompt):\n    return 'x'")

        assert any("_complete" in item for item in found)

    def test_pydantic_handler_is_flagged(self) -> None:
        found = find_review_items("except ValidationError as e:\n    pass")

        assert any("InputValidationError" in item for item in found)

    def test_legacy_cli_flags_are_flagged(self) -> None:
        found = find_review_items('subprocess.run(["promptkit", "run", "--name", "A"])')

        assert any("--set" in item for item in found)

    def test_clean_source_needs_no_review(self) -> None:
        assert find_review_items("x = 1\n") == []


class TestCli:
    def test_dry_run_does_not_write(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        target = tmp_path / "app.py"
        target.write_text(LEGACY)

        assert main([str(tmp_path)]) == 0
        assert target.read_text() == LEGACY
        assert "would rewrite" in capsys.readouterr().out

    def test_write_applies(self, tmp_path: Path) -> None:
        target = tmp_path / "app.py"
        target.write_text(LEGACY)
        main([str(tmp_path), "--write"])
        result = target.read_text()

        assert "get_model_pricing" not in result
        assert "from promptkit.pricing import get_pricing" in result
        assert "host=" in result

    def test_rewritten_imports_are_importable(self, tmp_path: Path) -> None:
        target = tmp_path / "app.py"
        target.write_text(
            "from promptkit.utils.tokens import estimate_tokens, get_model_pricing\n"
        )
        main([str(tmp_path), "--write"])

        compile(target.read_text(), str(target), "exec")

    def test_diff_is_shown_by_default(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "app.py").write_text(LEGACY)
        main([str(tmp_path)])

        assert "@@" in capsys.readouterr().out

    def test_diff_can_be_suppressed(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "app.py").write_text(LEGACY)
        main([str(tmp_path), "--no-diff"])

        assert "@@" not in capsys.readouterr().out

    def test_missing_target(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / "nope")]) == 1

    def test_single_file_target(self, tmp_path: Path) -> None:
        target = tmp_path / "app.py"
        target.write_text(LEGACY)

        assert main([str(target), "--write"]) == 0
        assert "get_pricing" in target.read_text()

    def test_virtualenvs_are_skipped(self, tmp_path: Path) -> None:
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib.py").write_text(LEGACY)
        (tmp_path / "app.py").write_text(LEGACY)

        assert [p.name for p in python_files(tmp_path)] == ["app.py"]
