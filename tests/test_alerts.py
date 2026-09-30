"""Tests for alerts.py: budget thresholds and goal milestones.

Main elements:
    Budget thresholds (80 % / 100 %), goal milestones and deadlines.

Course concepts exercised:
    Decision structures.
"""

from __future__ import annotations

from datetime import date

import pytest

from finance_tracker import alerts
from finance_tracker.tracker import FinanceTracker


@pytest.mark.parametrize(
    ("ratio", "level"),
    [(0.0, "OK"), (0.79, "OK"), (0.80, "WARNING"), (0.99, "WARNING"), (1.0, "EXCEEDED")],
)
def test_budget_level_thresholds(ratio: float, level: str) -> None:
    assert alerts.budget_level(ratio) == level


def test_check_budgets_latest_month(tracker: FinanceTracker) -> None:
    # February: Groceries 420/400 (105 %), Housing 1200/1300 (92 %), Dining 0/200.
    result = alerts.check_budgets(tracker)
    assert [(a.level, a.subject) for a in result] == [
        ("EXCEEDED", "Groceries"),
        ("WARNING", "Housing"),
    ]
    assert "over by $20.00" in result[0].message
    assert "$100.00 left" in result[1].message


def test_check_budgets_include_ok_and_specific_month(tracker: FinanceTracker) -> None:
    result = alerts.check_budgets(tracker, month="2025-01", include_ok=True)
    levels = {a.subject: a.level for a in result}
    assert levels == {"Dining Out": "OK", "Groceries": "OK", "Housing": "WARNING"}
    assert result[0].subject == "Housing"  # most severe first


def test_check_budgets_empty_tracker() -> None:
    assert alerts.check_budgets(FinanceTracker()) == []


def test_goal_milestones_and_deadlines(tracker: FinanceTracker) -> None:
    tracker.add_goal("Laptop", 1000, saved=1000)
    tracker.add_goal("Old Trip", 800, saved=100, deadline="2024-06-01")
    tracker.add_goal("New Bike", 600, saved=50)

    result = alerts.check_goals(tracker, today=date(2025, 3, 1))
    by_subject = {a.subject: a for a in result}

    assert by_subject["Old Trip"].level == "WARNING"
    assert "missed its deadline" in by_subject["Old Trip"].message
    assert by_subject["Emergency Fund"].level == "INFO"
    assert "50%" in by_subject["Emergency Fund"].message
    assert by_subject["Laptop"].level == "OK"
    assert "New Bike" not in by_subject  # 8 % — no milestone reached yet
    assert result[0].subject == "Old Trip"


def test_reached_milestone() -> None:
    assert alerts.reached_milestone(0.1) is None
    assert alerts.reached_milestone(0.76) == 0.75
    assert alerts.reached_milestone(1.0) == 1.0


def test_collect_alerts_and_str(tracker: FinanceTracker) -> None:
    result = alerts.collect_alerts(tracker, today=date(2025, 3, 1))
    assert len(result) == 3
    assert str(result[0]).startswith("[EXCEEDED] Groceries")


def test_exactly_at_limit_reads_limit_reached(tracker: FinanceTracker) -> None:
    tracker.set_budget("Housing", 1200)
    housing = next(a for a in alerts.check_budgets(tracker) if a.subject == "Housing")
    assert housing.level == "EXCEEDED"  # the spec treats 100 % as exceeded
    assert housing.message.endswith("limit reached")
