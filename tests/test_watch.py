from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from promptkit.cli.commands.watch import check, prompts_in, snapshot
from promptkit.cli.main import app
from tests.conftest import bump_mtime

runner = CliRunner()

CLEAN = (
    "name: clean\ndescription: A clean prompt\nversion: 1.0.0\n"
    "messages:\n  - role: system\n    template: Be brief.\n"
    "  - role: user\n    template: Hi {{ n }}\ninput_schema:\n  n: str\n"
)
BROKEN = "name: broken\ndescription: d\nversion: 1.0.0\ntemplate: Hi {{ undeclared }}\n"


class TestSnapshot:
    def test_tracks_watched_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.yaml").write_text(CLEAN)
        (tmp_path / "b.j2").write_text("x")
        (tmp_path / "c.png").write_bytes(b"\x00")

        assert {p.name for p in snapshot(tmp_path)} == {"a.yaml", "b.j2"}

    def test_a_single_file_target(self, tmp_path: Path) -> None:
        target = tmp_path / "a.yaml"
        target.write_text(CLEAN)

        assert list(snapshot(target)) == [target]

    def test_detects_a_change(self, tmp_path: Path) -> None:
        target = tmp_path / "a.yaml"
        target.write_text(CLEAN)
        before = snapshot(tmp_path)
        target.write_text(CLEAN + "\n")
        bump_mtime(target)

        assert snapshot(tmp_path) != before


class TestCheck:
    def test_clean_prompt_has_no_errors(self, tmp_path: Path) -> None:
        (tmp_path / "clean.yaml").write_text(CLEAN)
        errors, findings = check(tmp_path)

        assert (errors, findings) == (0, 0)

    def test_broken_prompt_reports_an_error(self, tmp_path: Path) -> None:
        (tmp_path / "broken.yaml").write_text(BROKEN)
        errors, _ = check(tmp_path)

        assert errors == 1

    def test_eval_suites_are_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "clean.yaml").write_text(CLEAN)
        (tmp_path / "clean.evals.yaml").write_text("cases: []\n")

        assert check(tmp_path) == (0, 0)

    def test_prompts_in_a_directory(self, tmp_path: Path) -> None:
        (tmp_path / "clean.yaml").write_text(CLEAN)

        assert [p.name for p in prompts_in(tmp_path)] == ["clean.yaml"]


class TestCommand:
    def test_once_exits_zero_when_clean(self, tmp_path: Path) -> None:
        (tmp_path / "clean.yaml").write_text(CLEAN)
        result = runner.invoke(app, ["watch", str(tmp_path), "--once"])

        assert result.exit_code == 0
        assert "clean" in result.stdout

    def test_once_exits_nonzero_on_an_error(self, tmp_path: Path) -> None:
        (tmp_path / "broken.yaml").write_text(BROKEN)
        result = runner.invoke(app, ["watch", str(tmp_path), "--once"])

        assert result.exit_code == 1
        assert "PK001" in result.stdout

    def test_missing_target_is_reported(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["watch", str(tmp_path / "nope"), "--once"])

        assert result.exit_code == 1

    def test_help_is_available(self) -> None:
        assert runner.invoke(app, ["watch", "--help"]).exit_code == 0
