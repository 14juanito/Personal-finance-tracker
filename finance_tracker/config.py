"""Project-wide paths and settings.

All paths are computed relative to this file with ``pathlib`` so the project works
from any working directory and on any operating system — no absolute paths are
hard-coded.

Course concepts illustrated:
    - File handling: ``pathlib.Path`` arithmetic.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
OUTPUT_DIR: Path = PROJECT_ROOT / "output"
CHARTS_DIR: Path = OUTPUT_DIR / "charts"

SAMPLE_JSON: Path = DATA_DIR / "sample_data.json"
SAMPLE_CSV: Path = DATA_DIR / "sample_transactions.csv"
# The user's own data lives here; it is git-ignored so personal data is never committed.
USER_DATA_FILE: Path = DATA_DIR / "my_finances.json"
