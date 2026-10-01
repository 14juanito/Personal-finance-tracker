"""Build the LaTeX project report and technical memo, then copy the PDFs to deliverables/.

Steps:
    1. Capture real screenshots (``tools/capture_screenshots.py``) into docs/figures/.
    2. Write ``docs/shared/generated/``: ``meta.tex`` (real test count, coverage,
       library versions, name field, date) and code excerpts extracted from the
       source with ``ast`` — the documents never contain hand-copied code.
    3. Compile ``docs/report/Project_Report.tex`` and ``docs/memo/Memo_Technique.tex``
       with ``latexmk -pdf``.
    4. Check the logs (no undefined reference, no overfull box above 10 pt) and the
       report length (5 to 8 pages), then copy both PDFs to deliverables/.

Usage:
    python tools/build_latex.py [--skip-capture] [--skip-tests]

Main elements:
    extract_function, write_snippets, write_meta, compile_tex, check_log, page_count,
    build, main.

Course concepts illustrated:
    Functions, dictionaries, file handling, ``ast`` parsing, subprocesses, exceptions.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from doc_assets import library_versions, test_stats
from submission_config import STUDENT_NAME, identity_lines

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / "docs" / "shared" / "generated"
DELIVERABLES = ROOT / "deliverables"
DOCUMENTS: dict[str, Path] = {
    "Project_Report": ROOT / "docs" / "report" / "Project_Report.tex",
    "Memo_Technique": ROOT / "docs" / "memo" / "Memo_Technique.tex",
}
REPORT_PAGES = (5, 8)
MAX_OVERFULL_PT = 10.0
# Excerpt name → (source file, qualified function name). Docstrings are omitted.
SNIPPETS: dict[str, tuple[str, str]] = {
    "prompt_amount": ("finance_tracker/cli.py", "ConsoleApp.prompt_amount"),
    "budget_level": ("finance_tracker/alerts.py", "budget_level"),
    "category_breakdown": ("finance_tracker/analytics.py", "category_breakdown"),
    "monthly_summary": ("finance_tracker/analytics.py", "monthly_summary"),
    "parse_amount": ("finance_tracker/models.py", "parse_amount"),
    "transaction_post_init": ("finance_tracker/models.py", "Transaction.__post_init__"),
    "tracker_init": ("finance_tracker/tracker.py", "FinanceTracker.__init__"),
    "tracker_filter": ("finance_tracker/tracker.py", "FinanceTracker.filter"),
    "load_json": ("finance_tracker/storage.py", "load_json"),
    "atomic_write": ("finance_tracker/storage.py", "_atomic_write"),
    "check_budgets": ("finance_tracker/alerts.py", "check_budgets"),
    "spending_trend": ("finance_tracker/analytics.py", "spending_trend"),
    "save_all_charts": ("finance_tracker/visualize.py", "save_all_charts"),
    "console_run": ("finance_tracker/cli.py", "ConsoleApp.run"),
    "main_dispatch": ("main.py", "main"),
    "dashboard_main": ("finance_tracker/dashboard.py", "main"),
    "check_structure": ("finance_tracker/storage.py", "_check_structure"),
    "gui_add_transaction": ("finance_tracker/gui_tkinter.py", "FinanceApp.add_transaction"),
    "kpis": ("finance_tracker/analytics.py", "kpis"),
    "to_dataframe": ("finance_tracker/analytics.py", "to_dataframe"),
    "add_transaction": ("finance_tracker/tracker.py", "FinanceTracker.add_transaction"),
    "exceptions_all": ("finance_tracker/exceptions.py", "*"),
    "category_pie": ("finance_tracker/visualize.py", "category_pie"),
    "md_escape": ("finance_tracker/dashboard.py", "md_escape"),
    "test_corrupted_json": ("tests/test_storage.py", "test_corrupted_json_is_backed_up"),
}
LATEX_SPECIAL = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\^{}",
}  # fmt: skip


def latex_escape(text: str) -> str:
    """Escape LaTeX special characters in plain text.

    Args:
        text: Text to print verbatim in a LaTeX document.

    Returns:
        The escaped text.
    """
    return "".join(LATEX_SPECIAL.get(char, char) for char in text)


def extract_function(path: Path, qualified_name: str) -> str:
    """Return the source of one function (without its docstring) or of classes.

    Args:
        path: Python source file.
        qualified_name: ``"function"``, ``"Class.method"`` or ``"*"`` for every
            top-level class of the module. Classes keep their docstring: without it
            a small class would look empty.

    Returns:
        The dedented source code, exactly as in the file (minus function docstrings).

    Raises:
        KeyError: If the function does not exist (the excerpt list is out of date).
    """
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    if qualified_name == "*":
        classes = [n for n in ast.parse(source).body if isinstance(n, ast.ClassDef)]
        start = min([classes[0].lineno, *(d.lineno for d in classes[0].decorator_list)]) - 1
        excerpt = "\n".join(lines[start : classes[-1].end_lineno])
        return textwrap.dedent(excerpt) + "\n"
    nodes: list[ast.AST] = [ast.parse(source)]
    for part in qualified_name.split("."):
        parent = nodes[-1]
        match = next(
            (
                n
                for n in ast.iter_child_nodes(parent)
                if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == part
            ),
            None,
        )
        if match is None:
            raise KeyError(f"{qualified_name} not found in {path}")
        nodes.append(match)
    func = nodes[-1]
    start = min([func.lineno, *(d.lineno for d in func.decorator_list)]) - 1
    body_lines = lines[start : func.end_lineno]
    first = func.body[0]
    if (
        not isinstance(func, ast.ClassDef)
        and isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        # Drop the docstring lines (relative to the excerpt start).
        del body_lines[first.lineno - 1 - start : first.end_lineno - start]
    return textwrap.dedent("\n".join(body_lines)) + "\n"


def write_snippets() -> list[Path]:
    """Extract every excerpt listed in ``SNIPPETS`` into the generated folder.

    Returns:
        Paths of the files written.
    """
    GENERATED.mkdir(parents=True, exist_ok=True)
    written = []
    for name, (file, qualified) in SNIPPETS.items():
        target = GENERATED / f"{name}.py"
        target.write_text(extract_function(ROOT / file, qualified), encoding="utf-8")
        written.append(target)
    return written


def write_data_samples() -> list[Path]:
    """Write short, real excerpts of the sample CSV and JSON files.

    Returns:
        Paths of the files written.
    """
    csv_lines = (ROOT / "data" / "sample_transactions.csv").read_text(encoding="utf-8")
    head = "\n".join(csv_lines.splitlines()[:5]) + "\n"
    payload = json.loads((ROOT / "data" / "sample_data.json").read_text(encoding="utf-8"))
    excerpt = {
        "version": payload["version"],
        "saved_at": payload["saved_at"],
        "transactions": payload["transactions"][:2],
        "budgets": payload["budgets"][:1],
        "goals": payload["goals"][:1],
    }
    csv_path = GENERATED / "sample_head.csv"
    json_path = GENERATED / "sample_excerpt.json"
    csv_path.write_text(head, encoding="utf-8")
    json_path.write_text(json.dumps(excerpt, indent=2) + "\n", encoding="utf-8")
    return [csv_path, json_path]


def write_meta(skip_tests: bool) -> Path:
    """Write ``meta.tex``: macros holding real figures and identity fields.

    Args:
        skip_tests: Do not run pytest (the macros then show "not run" markers).

    Returns:
        The path written.
    """
    _name_line, submitted = identity_lines()
    stats = test_stats(skip_tests)
    versions = library_versions()
    with (ROOT / "data" / "sample_transactions.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    months = sorted({row["date"][:7] for row in rows})
    name_field = latex_escape(STUDENT_NAME.strip()) or r"\underline{\hspace{6cm}}"
    macros = {
        "StudentNameField": name_field,
        "SubmissionDate": latex_escape(submitted),
        "TestCount": latex_escape(stats["tests"]),
        "CoveragePct": latex_escape(stats["coverage"]),
        "SampleCount": str(len(rows)),
        "SampleFirstMonth": months[0],
        "SampleLastMonth": months[-1],
    }
    for key, value in versions.items():
        macro = "Ver" + re.sub(r"[^A-Za-z]", "", key.title())
        macros[macro] = latex_escape(value)
    lines = ["% Generated by tools/build_latex.py — do not edit by hand."]
    lines += [f"\\newcommand{{\\{key}}}{{{value}}}" for key, value in macros.items()]
    path = GENERATED / "meta.tex"
    GENERATED.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def compile_tex(tex: Path) -> Path:
    """Compile a document with latexmk (pdflatex), output in a ``build/`` folder.

    Args:
        tex: The main ``.tex`` file.

    Returns:
        The produced PDF.

    Raises:
        SystemExit: If latexmk is missing or the compilation fails.
    """
    if shutil.which("latexmk") is None:
        raise SystemExit("Error: latexmk not found (install it, or put it on PATH).")
    result = subprocess.run(
        ["latexmk", "-pdf", "-g", "-interaction=nonstopmode", "-halt-on-error",
         "-file-line-error", "-outdir=build", tex.name],
        cwd=tex.parent,
        capture_output=True,
        text=True,
        # TeX tools print messages in the system locale (Latin-1 here): never crash on them.
        encoding="utf-8",
        errors="replace",
        check=False,
    )  # fmt: skip
    if result.returncode != 0:
        raise SystemExit(f"Error: compiling {tex.name} failed:\n{result.stdout[-3000:]}")
    return tex.parent / "build" / f"{tex.stem}.pdf"


def check_log(log: Path) -> list[str]:
    """Find LaTeX problems that do not stop the compilation.

    Args:
        log: The ``.log`` file of the final pass.

    Returns:
        Human-readable problems: undefined references/citations and overfull boxes
        wider than ``MAX_OVERFULL_PT``.
    """
    text = log.read_text(encoding="utf-8", errors="replace")
    problems = [
        line.strip()
        for line in text.splitlines()
        if re.search(r"(Reference|Citation) .* undefined|There were undefined", line)
    ]
    for match in re.finditer(r"Overfull \\[hv]box \((\d+(?:\.\d+)?)pt too \w+\)[^\n]*", text):
        if float(match.group(1)) > MAX_OVERFULL_PT:
            problems.append(match.group(0))
    return problems


def page_count(pdf: Path) -> int:
    """Number of pages of a PDF, read with ``pdfinfo`` (poppler).

    Args:
        pdf: The PDF file.

    Returns:
        The page count.
    """
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True)
    return int(re.search(r"^Pages:\s+(\d+)", info.stdout, re.M).group(1))


def build(skip_capture: bool = False, skip_tests: bool = False) -> dict[str, tuple[Path, int]]:
    """Run every step and return the delivered PDFs with their page counts.

    Args:
        skip_capture: Reuse the existing figures instead of capturing them again.
        skip_tests: Do not run pytest for the figures quoted in the documents.

    Returns:
        ``{document name: (deliverable path, pages)}``.

    Raises:
        SystemExit: If a compilation fails, a log check fails, or the report is
            outside 5–8 pages.
    """
    if not skip_capture:
        subprocess.run([sys.executable, "tools/capture_screenshots.py"], cwd=ROOT, check=True)
    write_snippets()
    write_data_samples()
    write_meta(skip_tests)
    delivered: dict[str, tuple[Path, int]] = {}
    for name, tex in DOCUMENTS.items():
        pdf = compile_tex(tex)
        problems = check_log(pdf.with_suffix(".log"))
        if problems:
            raise SystemExit(f"Error: {tex.name} has LaTeX problems:\n" + "\n".join(problems))
        pages = page_count(pdf)
        if name == "Project_Report" and not REPORT_PAGES[0] <= pages <= REPORT_PAGES[1]:
            raise SystemExit(f"Error: the report has {pages} pages (allowed: 5–8).")
        target = DELIVERABLES / pdf.name
        DELIVERABLES.mkdir(exist_ok=True)
        shutil.copy2(pdf, target)
        delivered[name] = (target, pages)
    return delivered


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Command-line arguments (None = ``sys.argv[1:]``).

    Returns:
        Process exit code (0; failures exit through ``SystemExit`` with a message).
    """
    parser = argparse.ArgumentParser(description="Build the LaTeX report and memo.")
    parser.add_argument("--skip-capture", action="store_true", help="reuse docs/figures/")
    parser.add_argument("--skip-tests", action="store_true", help="do not run pytest")
    args = parser.parse_args(argv)
    for name, (path, pages) in build(args.skip_capture, args.skip_tests).items():
        print(f"✓ {name}: {path.relative_to(ROOT)} — {pages} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
