"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from finance_tracker.tracker import FinanceTracker


@pytest.fixture
def tracker() -> FinanceTracker:
    """A small, deterministic tracker covering two months."""
    t = FinanceTracker()
    t.add_transaction("2025-01-01", 3000, "income", "Salary", "January pay")
    t.add_transaction("2025-01-03", 1200, "expense", "Housing", "Rent")
    t.add_transaction("2025-01-10", 150.50, "expense", "Groceries", "Weekly shop")
    t.add_transaction("2025-01-20", 80, "expense", "Dining Out", "Pizza night")
    t.add_transaction("2025-02-01", 3000, "income", "Salary", "February pay")
    t.add_transaction("2025-02-03", 1200, "expense", "Housing", "Rent")
    t.add_transaction("2025-02-12", 420, "expense", "Groceries", "Big stock-up")
    t.add_transaction("2025-02-15", 500, "income", "Freelance", "Website job")
    t.set_budget("Groceries", 400)
    t.set_budget("Dining Out", 200)
    t.set_budget("Housing", 1300)
    t.add_goal("Emergency Fund", 2000, saved=1100, deadline="2025-12-31")
    return t
