from __future__ import annotations

import json
from xml.etree.ElementTree import Element, SubElement, tostring

from rich.console import Console
from rich.table import Table

from promptkit.evals.runner import SuiteResult


def to_dict(result: SuiteResult) -> dict[str, object]:
    return {
        "prompt": result.prompt,
        "passed": result.passed,
        "failed": result.failed,
        "skipped": result.skipped,
        "total": result.total,
        "duration_seconds": round(result.duration_seconds, 4),
        "cost": round(result.cost, 6),
        "cases": [
            {
                "name": case.case,
                "passed": case.passed,
                "skipped": case.skipped,
                "duration_seconds": round(case.duration_seconds, 4),
                "cost": case.cost,
                "error": case.error,
                "assertions": [
                    {"kind": a.kind, "passed": a.passed, "detail": a.detail}
                    for a in case.assertions
                ],
            }
            for case in result.results
        ],
    }


def to_json(result: SuiteResult, indent: int = 2) -> str:
    return json.dumps(to_dict(result), indent=indent, sort_keys=False)


def to_junit(result: SuiteResult) -> str:
    suite = Element(
        "testsuite",
        name=f"promptkit.{result.prompt}",
        tests=str(result.total),
        failures=str(result.failed),
        skipped=str(result.skipped),
        time=f"{result.duration_seconds:.4f}",
    )

    for case in result.results:
        node = SubElement(
            suite,
            "testcase",
            classname=f"promptkit.{result.prompt}",
            name=case.case,
            time=f"{case.duration_seconds:.4f}",
        )

        if case.skipped:
            SubElement(node, "skipped")
            continue

        if case.error is not None:
            error = SubElement(node, "error", message=case.error)
            error.text = case.error
            continue

        if not case.passed:
            detail = "\n".join(
                f"{a.kind}: {a.detail or 'failed'}" for a in case.failures
            )
            failure = SubElement(node, "failure", message=detail.splitlines()[0])
            failure.text = detail

    return tostring(
        suite,
        encoding="unicode",
        xml_declaration=True,
    )


def to_terminal(result: SuiteResult, console: Console, verbose: bool = False) -> None:
    table = Table(title=f"Evals: {result.prompt}")
    table.add_column("Case", style="cyan")
    table.add_column("Result")
    table.add_column("Time", justify="right", style="dim")
    table.add_column("Detail")

    for case in result.results:
        if case.skipped:
            status = "[dim]skip[/dim]"
        elif case.passed:
            status = "[green]pass[/green]"
        else:
            status = "[red]fail[/red]"

        detail = case.error or "; ".join(
            f"{a.kind}: {a.detail}" for a in case.failures if a.detail
        )

        if verbose and case.passed and not case.skipped:
            detail = f"{len(case.assertions)} assertion(s) ok"

        table.add_row(case.case, status, f"{case.duration_seconds:.2f}s", detail[:80])

    console.print(table)
    summary = (
        f"{result.passed} passed, {result.failed} failed, {result.skipped} skipped"
        f" in {result.duration_seconds:.2f}s"
    )

    if result.cost:
        summary = f"{summary} (${result.cost:.6f})"

    console.print(summary)


__all__ = ["to_dict", "to_json", "to_junit", "to_terminal"]
