"""Tests for tools/build_source_zip.py.

Main elements:
    The source archive contains code and data but no caches or personal files.

Course concepts exercised:
    File handling, sets.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import build_source_zip  # noqa: E402


def test_zip_contains_code_and_data_but_no_junk(tmp_path: Path) -> None:
    output, count = build_source_zip.build(tmp_path / "src.zip")
    names = zipfile.ZipFile(output).namelist()
    assert count == len(names)
    prefix = build_source_zip.ARCHIVE_ROOT + "/"
    for required in (
        "main.py",
        "finance_tracker/models.py",
        "data/sample_transactions.csv",
        "data/sample_data.json",
        "requirements.txt",
        "tests/test_models.py",
    ):
        assert prefix + required in names
    forbidden = (".venv/", "__pycache__", "output/", ".claude/", "my_finances.json", ".pyc",
                 "/build/", ".aux", ".fdb_latexmk")  # fmt: skip
    assert not [n for n in names if any(f in n for f in forbidden)]
