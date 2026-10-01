"""Enforce the project's documentation standards so they cannot silently regress.

Main elements:
    Checks that every module has a header docstring with "Main elements" and "Course
    concepts", and that every function/class in the application and tools has a
    Google-style docstring (``Args:`` / ``Returns:`` where relevant) and type hints.

Course concepts exercised:
    Loops, decisions, sets, file handling (reading source files with ``pathlib``).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SOURCES = sorted([*ROOT.glob("finance_tracker/*.py"), ROOT / "main.py", *ROOT.glob("tools/*.py")])
REQUIRED_CONCEPTS = {
    "user input", "user output", "decision structure", "loop", "functions",
    "file handling", "exception handling", "list", "dictionary", "set", "oop", "pandas",
}  # fmt: skip


def _functions(tree: ast.AST) -> list[ast.FunctionDef]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_module_header(path: Path) -> None:
    doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
    assert "Main elements" in doc
    assert "concepts" in doc.lower()


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_google_docstrings_and_type_hints(path: Path) -> None:
    problems = []
    for node in _functions(ast.parse(path.read_text(encoding="utf-8"))):
        doc = ast.get_docstring(node)
        params = [a for a in node.args.args + node.args.kwonlyargs if a.arg not in {"self", "cls"}]
        if not doc:
            problems.append(f"{node.name}: no docstring")
            continue
        if params and node.name != "__post_init__" and "Args:" not in doc:
            problems.append(f"{node.name}: no Args section")
        returns_value = node.returns is not None and not (
            isinstance(node.returns, ast.Constant) and node.returns.value is None
        )
        is_property = any(getattr(d, "id", "") == "property" for d in node.decorator_list)
        if returns_value and not is_property and "Returns:" not in doc and "Yields:" not in doc:
            problems.append(f"{node.name}: no Returns section")
        if any(a.annotation is None for a in params):
            problems.append(f"{node.name}: missing parameter type hints")
        if node.returns is None and node.name != "__init__":
            problems.append(f"{node.name}: missing return type hint")
    assert problems == []


def test_every_course_concept_is_tagged() -> None:
    tags = " ".join(
        line.split("# Concept:", 1)[1].lower()
        for path in SOURCES
        for line in path.read_text(encoding="utf-8").splitlines()
        if "# Concept:" in line
    )
    missing = {concept for concept in REQUIRED_CONCEPTS if concept not in tags}
    assert missing == set()
