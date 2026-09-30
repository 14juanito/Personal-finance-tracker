"""Tests for the sample data generator and the committed sample files."""

from __future__ import annotations

import sys
from pathlib import Path

from finance_tracker.config import SAMPLE_CSV, SAMPLE_JSON
from finance_tracker.tracker import FinanceTracker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import generate_sample_data  # noqa: E402


def test_generator_is_deterministic_and_realistic() -> None:
    first = generate_sample_data.build_tracker(seed=1)
    second = generate_sample_data.build_tracker(seed=1)
    assert [t.amount for t in first.transactions] == [t.amount for t in second.transactions]
    assert 270 <= len(first.transactions) <= 340
    assert len(first.months()) == generate_sample_data.MONTHS
    assert first.balance() > 0  # the fictional student saves money overall


def test_generator_cli_writes_files(tmp_path: Path) -> None:
    csv_path, json_path = tmp_path / "t.csv", tmp_path / "d.json"
    assert generate_sample_data.main(["--csv", str(csv_path), "--json", str(json_path)]) == 0
    from_csv, _ = FinanceTracker.from_csv(csv_path)
    from_json, _ = FinanceTracker.load_json(json_path)
    assert len(from_csv.transactions) == len(from_json.transactions)
    assert from_json.budgets and from_json.goals


def test_committed_sample_files_are_valid() -> None:
    tracker, warnings = FinanceTracker.load_json(SAMPLE_JSON)
    assert warnings == []
    csv_tracker, csv_warnings = FinanceTracker.from_csv(SAMPLE_CSV)
    assert csv_warnings == []
    assert {t.id for t in tracker.transactions} == {t.id for t in csv_tracker.transactions}
