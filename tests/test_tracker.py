"""Tests for tracker.py: CRUD, search, filter, summaries, persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from finance_tracker.exceptions import (
    InvalidGoalError,
    InvalidTransactionError,
    StorageError,
    TransactionNotFoundError,
)
from finance_tracker.tracker import FinanceTracker


def test_totals_and_balance(tracker: FinanceTracker) -> None:
    assert tracker.total("income") == 6500
    assert tracker.total("expense") == 3050.5
    assert tracker.balance() == 3449.5
    assert tracker.balance("2025-01") == 1569.5
    assert tracker.months() == ["2025-01", "2025-02"]
    assert tracker.latest_month() == "2025-02"


def test_spending_by_category_sorted_desc(tracker: FinanceTracker) -> None:
    by_cat = tracker.spending_by_category()
    assert list(by_cat) == ["Housing", "Groceries", "Dining Out"]
    assert by_cat["Groceries"] == 570.5
    assert tracker.spending_by_category("2025-02") == {"Housing": 1200, "Groceries": 420}


def test_new_category_is_added_to_set(tracker: FinanceTracker) -> None:
    tracker.add_transaction("2025-02-20", 30, "expense", "pet care")
    tracker.add_transaction("2025-02-21", 30, "expense", "PET CARE")
    assert "Pet Care" in tracker.categories
    assert "Pet Care" in tracker.expense_categories()
    assert "Pet Care" not in tracker.income_categories()


def test_invalid_add_does_not_store(tracker: FinanceTracker) -> None:
    before = len(tracker.transactions)
    with pytest.raises(InvalidTransactionError):
        tracker.add_transaction("2025-02-20", "-10", "expense", "Food")
    assert len(tracker.transactions) == before


def test_update_and_delete(tracker: FinanceTracker) -> None:
    target = tracker.search("pizza")[0]
    updated = tracker.update_transaction(target.id, amount="95.25", category="entertainment")
    assert updated.id == target.id
    assert tracker.get_transaction(target.id).amount == 95.25
    assert "Entertainment" in tracker.categories

    removed = tracker.delete_transaction(target.id)
    assert removed.id == target.id
    with pytest.raises(TransactionNotFoundError):
        tracker.get_transaction(target.id)


def test_failed_update_keeps_original(tracker: FinanceTracker) -> None:
    target = tracker.transactions[1]
    with pytest.raises(InvalidTransactionError):
        tracker.update_transaction(target.id, amount="free")
    with pytest.raises(InvalidTransactionError, match="Cannot update"):
        tracker.update_transaction(target.id, colour="red")
    assert tracker.transactions[1] is target


def test_search_is_case_insensitive(tracker: FinanceTracker) -> None:
    assert len(tracker.search("RENT")) == 2
    assert len(tracker.search("groceries")) == 2  # matches the category name
    assert tracker.search("   ") == []


def test_filter_combines_criteria(tracker: FinanceTracker) -> None:
    result = tracker.filter(kind="expense", start="2025-01-05", end="2025-02-28", min_amount=100)
    assert [t.description for t in result] == ["Weekly shop", "Rent", "Big stock-up"]
    assert len(tracker.filter(categories=["groceries"])) == 2
    assert len(tracker.filter(max_amount=100)) == 1
    assert [t.date.day for t in tracker.sorted_transactions()][:2] == [15, 12]


def test_budgets(tracker: FinanceTracker) -> None:
    tracker.set_budget("groceries", 450)
    assert tracker.budgets["Groceries"].monthly_limit == 450
    assert tracker.remove_budget("GROCERIES") is True
    assert tracker.remove_budget("Groceries") is False


def test_goals(tracker: FinanceTracker) -> None:
    goal = tracker.contribute_to_goal("Emergency  Fund", 400)
    assert goal.saved == 1500
    with pytest.raises(InvalidGoalError, match="already exists"):
        tracker.add_goal("Emergency Fund", 10)
    with pytest.raises(InvalidGoalError, match="No goal"):
        tracker.contribute_to_goal("Vacation", 10)
    assert tracker.remove_goal("Emergency Fund") is True
    assert tracker.goals == {}


def test_json_persistence_round_trip(tracker: FinanceTracker, tmp_path: Path) -> None:
    path = tracker.save_json(tmp_path / "state.json")
    loaded, warnings = FinanceTracker.load_json(path)
    assert warnings == []
    assert loaded.transactions == tracker.transactions
    assert loaded.budgets == tracker.budgets
    assert loaded.goals == tracker.goals


def test_csv_export_import_skips_duplicates(tracker: FinanceTracker, tmp_path: Path) -> None:
    path = tracker.export_csv(tmp_path / "tx.csv")
    fresh, warnings = FinanceTracker.from_csv(path)
    assert len(fresh.transactions) == len(tracker.transactions)
    assert warnings == []

    warnings = tracker.import_csv(path)
    assert len(tracker.transactions) == 8
    assert warnings == ["Ignored 8 transaction(s) already present."]

    empty = FinanceTracker()
    assert empty.import_csv(path) == []
    assert len(empty.transactions) == 8


def test_from_csv_missing_file(tmp_path: Path) -> None:
    with pytest.raises(StorageError):
        FinanceTracker.from_csv(tmp_path / "missing.csv")


def test_empty_tracker() -> None:
    empty = FinanceTracker()
    assert empty.balance() == 0
    assert empty.latest_month() is None
    assert empty.spending_by_category() == {}
