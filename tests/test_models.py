"""Tests for models.py and exceptions.py."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from finance_tracker.exceptions import (
    FinanceTrackerError,
    InvalidBudgetError,
    InvalidGoalError,
    InvalidTransactionError,
    TransactionNotFoundError,
)
from finance_tracker.models import (
    Budget,
    SavingsGoal,
    Transaction,
    normalize_category,
    parse_amount,
    parse_date,
)


def test_transaction_normalizes_fields() -> None:
    t = Transaction(
        date="2025-03-14", amount="$1,234.567", kind=" Expense ", category="  dining   out "
    )
    assert t.date == date(2025, 3, 14)
    assert t.amount == 1234.57
    assert t.kind == "expense"
    assert t.category == "Dining Out"
    assert t.signed_amount == -1234.57
    assert t.month == "2025-03"
    assert len(t.id) == 8


def test_income_has_positive_signed_amount() -> None:
    t = Transaction(date=date(2025, 1, 1), amount=100, kind="income", category="Salary")
    assert not t.is_expense
    assert t.signed_amount == 100


@pytest.mark.parametrize("amount", ["abc", "", 0, -5, "nan", "inf", 2_000_000, True])
def test_invalid_amounts_are_rejected(amount: object) -> None:
    with pytest.raises(InvalidTransactionError):
        Transaction(date="2025-01-01", amount=amount, kind="expense", category="Food")


@pytest.mark.parametrize("bad_date", ["2025-13-01", "01/02/2025", "yesterday", ""])
def test_invalid_dates_are_rejected(bad_date: str) -> None:
    with pytest.raises(InvalidTransactionError, match="Invalid date"):
        parse_date(bad_date)


def test_parse_date_accepts_datetime() -> None:
    assert parse_date(datetime(2025, 5, 6, 12, 30)) == date(2025, 5, 6)


def test_invalid_kind_and_empty_category() -> None:
    with pytest.raises(InvalidTransactionError, match="Invalid kind"):
        Transaction(date="2025-01-01", amount=5, kind="transfer", category="Food")
    with pytest.raises(InvalidTransactionError, match="Category"):
        Transaction(date="2025-01-01", amount=5, kind="expense", category="   ")


def test_description_too_long() -> None:
    with pytest.raises(InvalidTransactionError, match="Description"):
        Transaction(
            date="2025-01-01", amount=5, kind="expense", category="Food", description="x" * 200
        )


def test_transaction_dict_round_trip() -> None:
    original = Transaction(
        date="2025-02-02", amount=9.99, kind="expense", category="Fun", description="Movie"
    )
    clone = Transaction.from_dict(original.to_dict())
    assert clone == original


def test_from_dict_missing_field() -> None:
    with pytest.raises(InvalidTransactionError, match="Missing field"):
        Transaction.from_dict({"date": "2025-01-01", "amount": 3})


def test_parse_amount_and_category_helpers() -> None:
    assert parse_amount(" 12.5 ") == 12.5
    assert normalize_category("GROCERIES") == "Groceries"


def test_savings_goal_progress_and_contribution() -> None:
    goal = SavingsGoal(name=" Trip  to Japan ", target=1000, saved=250, deadline="2026-06-01")
    assert goal.name == "Trip to Japan"
    assert goal.progress == 0.25
    assert goal.remaining == 750
    goal.contribute("800")
    assert goal.saved == 1050
    assert goal.is_complete
    assert goal.progress == 1.0
    assert goal.remaining == 0


def test_savings_goal_validation() -> None:
    with pytest.raises(InvalidGoalError):
        SavingsGoal(name="", target=100)
    with pytest.raises(InvalidGoalError):
        SavingsGoal(name="Car", target=-1)
    with pytest.raises(InvalidGoalError):
        SavingsGoal(name="Car", target=100, saved=-5)
    with pytest.raises(InvalidGoalError):
        SavingsGoal(name="Car", target=100, saved="lots")
    with pytest.raises(InvalidGoalError):
        SavingsGoal(name="Car", target=100, deadline="soon")
    with pytest.raises(InvalidGoalError):
        SavingsGoal(name="Car", target=100).contribute(0)


def test_goal_and_budget_round_trip() -> None:
    goal = SavingsGoal(name="Car", target=5000, saved=100, deadline="2026-01-01")
    assert SavingsGoal.from_dict(goal.to_dict()) == goal
    no_deadline = SavingsGoal.from_dict({"name": "Laptop", "target": 900, "deadline": ""})
    assert no_deadline.deadline is None
    budget = Budget(category="groceries", monthly_limit=400)
    assert Budget.from_dict(budget.to_dict()) == budget
    assert budget.usage(300) == 0.75
    with pytest.raises(InvalidGoalError):
        SavingsGoal.from_dict({"target": 1})
    with pytest.raises(InvalidBudgetError):
        Budget.from_dict({"category": "Food"})


def test_budget_validation() -> None:
    with pytest.raises(InvalidBudgetError):
        Budget(category="", monthly_limit=100)
    with pytest.raises(InvalidBudgetError):
        Budget(category="Food", monthly_limit="zero")


def test_exception_hierarchy() -> None:
    # The UI relies on catching every app error through the base class.
    assert issubclass(InvalidTransactionError, FinanceTrackerError)
    assert issubclass(InvalidTransactionError, ValueError)
    assert str(TransactionNotFoundError("No transaction with id 'x'")) == (
        "No transaction with id 'x'"
    )
