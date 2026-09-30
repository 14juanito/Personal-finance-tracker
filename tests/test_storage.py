"""Tests for storage.py: JSON/CSV round-trips, missing and corrupted files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finance_tracker import storage
from finance_tracker.exceptions import StorageError
from finance_tracker.models import Budget, SavingsGoal, Transaction


@pytest.fixture
def sample() -> list[Transaction]:
    return [
        Transaction(date="2025-01-01", amount=2000, kind="income", category="Salary"),
        Transaction(
            date="2025-01-02",
            amount=45.5,
            kind="expense",
            category="Groceries",
            description='Milk, eggs & "bread"',  # comma + quotes stress the CSV quoting
        ),
    ]


def test_json_round_trip(tmp_path: Path, sample: list[Transaction]) -> None:
    budgets = {"Groceries": Budget("Groceries", 300)}
    goals = {"Car": SavingsGoal("Car", 5000, 250, "2026-01-01")}
    path = storage.save_json(tmp_path / "nested" / "data.json", sample, budgets, goals)

    state = storage.load_json(path)
    assert state.transactions == sample
    assert state.budgets == budgets
    assert state.goals == goals
    assert state.warnings == []
    # No temporary files may be left behind by the atomic write.
    assert [p.name for p in path.parent.iterdir()] == ["data.json"]


def test_load_json_missing_file_returns_empty_state(tmp_path: Path) -> None:
    state = storage.load_json(tmp_path / "absent.json")
    assert state.transactions == []
    assert "starting with empty data" in state.warnings[0]


def test_corrupted_json_is_backed_up(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text('{"transactions": [ {"date": ', encoding="utf-8")

    state = storage.load_json(path)

    assert state.transactions == []
    assert "corrupted" in state.warnings[0]
    assert not path.exists()
    backups = list(tmp_path.glob("data.json.corrupted-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8").startswith('{"transactions"')


def test_corrupted_json_without_recovery_raises(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")  # valid JSON, wrong shape
    with pytest.raises(StorageError, match="Corrupted"):
        storage.load_json(path, recover=False)
    assert path.exists()


def test_invalid_records_are_skipped_not_fatal(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    payload = {
        "transactions": [
            {"date": "2025-01-01", "amount": 10, "kind": "expense", "category": "Food"},
            {"date": "not-a-date", "amount": 10, "kind": "expense", "category": "Food"},
            {"date": "2025-01-02", "amount": -3, "kind": "expense", "category": "Food"},
            "garbage",
        ],
        "budgets": [{"category": "Food", "monthly_limit": 0}],
        "goals": [{"name": "", "target": 10}],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    state = storage.load_json(path)

    assert len(state.transactions) == 1
    assert state.budgets == {}
    assert state.goals == {}
    assert len(state.warnings) == 5


def test_csv_round_trip(tmp_path: Path, sample: list[Transaction]) -> None:
    path = storage.save_csv(tmp_path / "tx.csv", sample)
    header = path.read_text(encoding="utf-8").splitlines()[0]
    assert header == ",".join(storage.CSV_FIELDS)
    state = storage.load_csv(path)
    assert state.transactions == sample


def test_empty_csv_with_header_only(tmp_path: Path) -> None:
    path = storage.save_csv(tmp_path / "empty.csv", [])
    assert storage.load_csv(path).transactions == []


def test_csv_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(StorageError, match="not found"):
        storage.load_csv(tmp_path / "nope.csv")


def test_csv_missing_columns_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("date,amount\n2025-01-01,5\n", encoding="utf-8")
    with pytest.raises(StorageError, match="missing columns: category, kind"):
        storage.load_csv(path)


def test_csv_bad_rows_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "rows.csv"
    path.write_text(
        "date,amount,kind,category,description\n"
        "2025-01-01,10,expense,Food,ok\n"
        "2025-01-02,ten,expense,Food,bad amount\n"
        "2025-01-03,5,income,Gifts,ok\n",
        encoding="utf-8",
    )
    state = storage.load_csv(path)
    assert len(state.transactions) == 2
    assert state.warnings == ["Skipped CSV line 3: Invalid amount 'ten': not a number"]


def test_csv_binary_garbage_raises(tmp_path: Path) -> None:
    path = tmp_path / "binary.csv"
    path.write_bytes(b"\xff\xfe\x00\x81garbage")
    with pytest.raises(StorageError):
        storage.load_csv(path)


def test_write_to_unwritable_location_raises(tmp_path: Path, sample: list[Transaction]) -> None:
    blocker = tmp_path / "file.txt"
    blocker.write_text("I am a file, not a folder", encoding="utf-8")
    with pytest.raises(StorageError, match="Could not write"):
        storage.save_json(blocker / "data.json", sample)


@pytest.mark.parametrize(
    "content",
    ['{"transactions": null}', '{"transactions": 5}', '{"budgets": {"a": 1}}'],
)
def test_wrong_structure_is_treated_as_corrupted(tmp_path: Path, content: str) -> None:
    # Regression: valid JSON with the wrong shape used to crash every interface.
    path = tmp_path / "data.json"
    path.write_text(content, encoding="utf-8")
    state = storage.load_json(path)
    assert state.transactions == []
    assert "corrupted" in state.warnings[0]
    with pytest.raises(StorageError):
        path.write_text(content, encoding="utf-8")
        storage.load_json(path, recover=False)


def test_duplicate_ids_are_skipped(tmp_path: Path, sample: list[Transaction]) -> None:
    path = storage.save_json(tmp_path / "d.json", [sample[0], sample[0], sample[1]])
    state = storage.load_json(path)
    assert len(state.transactions) == 2
    assert "duplicate id" in state.warnings[0]
    csv_path = storage.save_csv(tmp_path / "d.csv", [sample[1], sample[1]])
    csv_state = storage.load_csv(csv_path)
    assert len(csv_state.transactions) == 1
    assert "duplicate id" in csv_state.warnings[0]


def test_excel_csv_with_bom_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "excel.csv"
    path.write_bytes("date,amount,kind,category\n2025-01-01,10,expense,Food\n".encode("utf-8-sig"))
    assert len(storage.load_csv(path).transactions) == 1
