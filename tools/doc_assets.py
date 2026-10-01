"""Shared assets for the documents: real test figures, library versions, diagram.

Main elements:
    test_stats: run pytest with coverage and return the real numbers.
    library_versions: installed versions of the libraries the project depends on.
    draw_architecture: layered architecture diagram (PNG) used by the slide deck.

Course concepts illustrated:
    Functions, dictionaries, subprocesses, file handling (JSON coverage report).
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
ARCHITECTURE_PNG = ROOT / "docs" / "figures" / "architecture.png"
# Distribution names as installed by pip (requirements.txt).
PACKAGES: tuple[str, ...] = (
    "pandas", "matplotlib", "plotly", "streamlit", "pillow", "python-pptx", "python-docx",
    "playwright", "rich", "pytest", "pytest-cov", "ruff",
)  # fmt: skip


def library_versions() -> dict[str, str]:
    """Versions of Python, Tk and every third-party package used by the project.

    Returns:
        Mapping name → version string (``"not installed"`` when missing).
    """
    import tkinter

    versions = {"python": platform.python_version(), "tkinter": str(tkinter.TkVersion)}
    for package in PACKAGES:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not installed"
    return versions


def test_stats(skip: bool) -> dict[str, str]:
    """Run pytest with coverage and return the numbers quoted in the report.

    Args:
        skip: Do not run the tests (placeholder markers are returned instead).

    Returns:
        ``{"tests": count, "coverage": percent}`` as strings.

    Raises:
        SystemExit: If the test suite fails.
    """
    if skip:
        # Visible markers instead of invented numbers: a draft built without tests
        # must never look like it quotes real results.
        return {"tests": "[tests not run]", "coverage": "[coverage not measured]"}
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "coverage.json"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--cov", f"--cov-report=json:{report}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise SystemExit("Tests failed — fix them before building the report.")
        passed = re.search(r"(\d+) passed", result.stdout)
        coverage = json.loads(report.read_text(encoding="utf-8"))["totals"]["percent_covered"]
    return {"tests": passed.group(1) if passed else "?", "coverage": f"{coverage:.0f}"}


def draw_architecture(path: Path = ARCHITECTURE_PNG) -> Path:
    """Draw the layered architecture diagram and save it as PNG.

    Args:
        path: Destination image.

    Returns:
        The path written.
    """
    fig = Figure(figsize=(10, 6.2), dpi=160)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 62)
    ax.axis("off")

    layers = [
        (
            50,
            "User interfaces",
            "#E3F2FD",
            [
                "main.py\n(cli | gui | demo)",
                "cli.py\nconsole menu",
                "gui_tkinter.py\nTkinter window",
                "dashboard.py\nStreamlit",
            ],
        ),
        (
            35,
            "Application logic",
            "#E8F5E9",
            [
                "tracker.py\nFinanceTracker",
                "alerts.py\nbudget alerts",
                "analytics.py\npandas",
                "visualize.py\nmatplotlib",
            ],
        ),
        (
            20,
            "Domain & persistence",
            "#FFF3E0",
            [
                "models.py\ndataclasses",
                "exceptions.py\nerror classes",
                "storage.py\nJSON + CSV",
                "config.py\npaths",
            ],
        ),
        (
            5,
            "Files",
            "#F3E5F5",
            ["data/sample_data.json", "data/*.csv", "output/charts/*.png", "data/my_finances.json"],
        ),
    ]
    for y, title, color, boxes in layers:
        ax.add_patch(
            FancyBboxPatch((1, y - 1), 98, 12, boxstyle="round,pad=0.3", fc=color, ec="#BDBDBD")
        )
        ax.text(2.5, y + 9.7, title, fontsize=10, weight="bold", color="#424242")
        for index, label in enumerate(boxes):
            x = 5 + index * 23.5
            ax.add_patch(
                FancyBboxPatch(
                    (x, y + 0.5), 19, 7, boxstyle="round,pad=0.4", fc="white", ec="#757575"
                )
            )
            ax.text(x + 9.5, y + 4, label, ha="center", va="center", fontsize=8.5)

    # One arrow between consecutive layers: each layer only uses the layer below it,
    # which reads more clearly than a web of module-to-module arrows.
    for upper, lower in zip(layers, layers[1:], strict=False):
        y_top, y_bottom = upper[0] - 1.3, lower[0] + 11.3
        for x in (27, 73):
            ax.add_patch(
                FancyArrowPatch(
                    (x, y_top),
                    (x, y_bottom),
                    arrowstyle="-|>",
                    mutation_scale=16,
                    color="#546E7A",
                    lw=1.6,
                )
            )
        ax.text(
            50,
            (y_top + y_bottom) / 2,
            "uses",
            ha="center",
            va="center",
            fontsize=8,
            color="#546E7A",
            style="italic",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    return path
