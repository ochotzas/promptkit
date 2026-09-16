from __future__ import annotations

import argparse
import difflib
import re
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "build",
    "dist",
}


@dataclass(frozen=True, slots=True)
class Rewrite:
    name: str
    pattern: re.Pattern[str]
    replacement: str | Callable[[re.Match[str]], str]
    note: str


TOKENS_IMPORT = re.compile(r"^from promptkit\.utils\.tokens import (.+)$", re.MULTILINE)


def _split_tokens_import(match: re.Match[str]) -> str:
    names = [n.strip() for n in match.group(1).split(",")]

    if "get_model_pricing" not in names:
        return match.group(0)

    remaining = [n for n in names if n != "get_model_pricing"]
    lines = ["from promptkit.pricing import get_pricing"]

    if remaining:
        lines.append(f"from promptkit.utils.tokens import {', '.join(remaining)}")

    return "\n".join(lines)


REWRITES: tuple[Rewrite, ...] = (
    Rewrite(
        "get-model-pricing-import",
        TOKENS_IMPORT,
        _split_tokens_import,
        "get_pricing moved to promptkit.pricing and returns per-1M rates",
    ),
    Rewrite(
        "get-model-pricing",
        re.compile(r"\bget_model_pricing\b"),
        "get_pricing",
        "get_model_pricing was removed; get_pricing returns per-1M rates",
    ),
    Rewrite(
        "ollama-base-url",
        re.compile(r"(OllamaEngine\([^)]*?)\bbase_url\s*="),
        r"\1host=",
        "OllamaEngine takes host= rather than base_url=",
    ),
)

REVIEW_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "prompt-template-property",
        re.compile(r"\b\w+\.template\b(?!\s*=)"),
        "Prompt.template was removed. If this is a PromptKit prompt, use .messages or "
        ".joined_template. Not rewritten automatically because '.template' is a common "
        "attribute name on other objects",
    ),
    (
        "run_prompt-returns-completion",
        re.compile(r"\brun_prompt(_async)?\s*\("),
        "run_prompt now returns a Completion; use .text, or run_prompt_text",
    ),
    (
        "engine-generate",
        re.compile(r"def\s+generate\s*\(\s*self"),
        "custom engines implement _complete(messages) returning a Completion",
    ),
    (
        "pydantic-validation-error",
        re.compile(r"except\s+[\w.]*ValidationError"),
        "pydantic.ValidationError is now InputValidationError",
    ),
    (
        "cli-legacy-flags",
        re.compile(r"--(name|context)\b"),
        "--name and --context were removed; use --set key=value",
    ),
)


@dataclass(slots=True)
class FileReport:
    path: Path
    applied: list[str]
    review: list[str]
    diff: list[str]

    @property
    def changed(self) -> bool:
        return bool(self.applied)


def python_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        yield root

        return

    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue

        yield path


def apply_rewrites(source: str) -> tuple[str, list[str]]:
    applied: list[str] = []
    result = source

    for rewrite in REWRITES:
        replaced, count = rewrite.pattern.subn(rewrite.replacement, result)

        if count:
            applied.append(f"{rewrite.name} ({count}): {rewrite.note}")
            result = replaced

    return result, applied


def find_review_items(source: str) -> list[str]:
    found: list[str] = []

    for name, pattern, note in REVIEW_PATTERNS:
        matches = len(pattern.findall(source))

        if matches:
            found.append(f"{name} ({matches}): {note}")

    return found


def process(path: Path, write: bool) -> FileReport:
    source = path.read_text(encoding="utf-8")
    rewritten, applied = apply_rewrites(source)
    review = find_review_items(source)
    diff = list(
        difflib.unified_diff(
            source.splitlines(),
            rewritten.splitlines(),
            fromfile=str(path),
            tofile=f"{path} (rewritten)",
            lineterm="",
            n=1,
        )
    )

    if applied and write:
        path.write_text(rewritten, encoding="utf-8")

    return FileReport(path=path, applied=applied, review=review, diff=diff)


def run(target: Path, write: bool, show_diff: bool = True) -> int:
    reports = [process(path, write) for path in python_files(target)]
    changed = [r for r in reports if r.changed]
    review = [r for r in reports if r.review]

    for report in changed:
        verb = "rewrote" if write else "would rewrite"
        print(f"{verb} {report.path}")

        for item in report.applied:
            print(f"    {item}")

        if show_diff:
            for line in report.diff:
                if not line.startswith(("---", "+++")):
                    print(f"    {line}")

    if review:
        print("\nNeeds a human:")

        for report in review:
            print(f"  {report.path}")

            for item in report.review:
                print(f"    {item}")

    print(
        f"\n{len(reports)} file(s) scanned, {len(changed)} "
        f"{'changed' if write else 'would change'}, {len(review)} need review"
    )

    if not write and changed:
        print("Review the diff above, then re-run with --write to apply.")
        print("Work on a clean git tree so you can undo it.")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m promptkit.codemod",
        description="Update code for PromptKit 1.0. Dry run unless --write is given.",
    )
    parser.add_argument("target", type=Path, help="File or directory to scan")
    parser.add_argument("--write", action="store_true", help="Apply the rewrites")
    parser.add_argument(
        "--no-diff", action="store_true", help="Do not print the proposed diff"
    )
    args = parser.parse_args(argv)

    if not args.target.exists():
        print(f"error: {args.target} does not exist", file=sys.stderr)

        return 1

    return run(args.target, args.write, show_diff=not args.no_diff)


if __name__ == "__main__":
    raise SystemExit(main())
