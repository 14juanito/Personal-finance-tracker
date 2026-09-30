"""Package the source code and data into deliverables/finance_tracker_source.zip.

Included: Python code (main.py, finance_tracker/, tools/, tests/), the sample CSV/JSON
data, docs/ images and the project files (README, requirements, pyproject, PLAN,
DECISIONS, DEV_LOG). Excluded: virtual environments, caches, generated output, tool
folders such as .claude/, deliverables/ and the user's personal data file.

Usage:
    python tools/build_source_zip.py

Main elements:
    is_excluded, collect, build.

Course concepts illustrated:
    File handling (``pathlib``, ``zipfile``), sets for fast exclusion checks.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "deliverables" / "finance_tracker_source.zip"
ARCHIVE_ROOT = "Personal-finance-tracker"
INCLUDE_DIRS = ("finance_tracker", "tools", "tests", "data", "docs")
INCLUDE_FILES = (
    "main.py",
    "README.md",
    "requirements.txt",
    "pyproject.toml",
    ".gitignore",
    "PLAN.md",
    "DECISIONS.md",
    "DEV_LOG.md",
)
EXCLUDED_PARTS = {".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "output", ".claude"}
EXCLUDED_NAMES = {"my_finances.json", ".DS_Store", ".coverage"}


def is_excluded(path: Path) -> bool:
    """Tell whether a file must stay out of the archive.

    Args:
        path: File inside the project.

    Returns:
        True for caches, generated output, personal data, backups and logs.
    """
    relative = path.relative_to(ROOT)
    return (
        bool(EXCLUDED_PARTS & set(relative.parts))
        or path.name in EXCLUDED_NAMES
        or ".corrupted-" in path.name
        or path.suffix in {".pyc", ".log"}
    )


def collect() -> list[Path]:
    """List every file to package.

    Returns:
        Sorted paths (sorting makes the archive reproducible).
    """
    files = [ROOT / name for name in INCLUDE_FILES if (ROOT / name).is_file()]
    for folder in INCLUDE_DIRS:
        files.extend(p for p in (ROOT / folder).rglob("*") if p.is_file())
    return sorted(p for p in files if not is_excluded(p))


def build(output: Path = OUTPUT) -> tuple[Path, int]:
    """Write the zip file.

    Args:
        output: Destination ``.zip`` file.

    Returns:
        ``(path written, number of files)``.
    """
    files = collect()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, f"{ARCHIVE_ROOT}/{path.relative_to(ROOT).as_posix()}")
    return output, len(files)


if __name__ == "__main__":
    path, count = build()
    print(f"✓ {path} — {count} files, {path.stat().st_size / 1024:.0f} KB")
