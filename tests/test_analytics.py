"""Tests for analytics.py: pandas calculations.

Main elements:
    Every pandas calculation against numbers computed by hand.

Course concepts exercised:
    pandas.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from finance_tracker import analytics
from finance_tracker.tracker import FinanceTracker


@pytest.fixture
def df(tracker: FinanceTracker) -> pd.DataFrame:
    return analytics.to_dataframe(tracker.transactions)


def test_to_dataframe_types(df: pd.DataFrame) -> None:
    assert len(df) == 8
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert df["date"].is_monotonic_increasing
    assert df["signed_amount"].sum() == pytest.approx(3449.5)
    assert set(df["month"]) == {"2025-01", "2025-02"}


def test_monthly_summary(df: pd.DataFrame) -> None:
    summary = analytics.monthly_summary(df)
    jan = summary.loc["2025-01"]
    assert jan["income"] == 3000
    assert jan["expense"] == 1430.5
    assert jan["net"] == 1569.5
    assert jan["savings_rate"] == pytest.approx(52.32, abs=0.01)
    assert summary.loc["2025-02", "income"] == 3500


def test_monthly_summary_without_income() -> None:
    tracker = FinanceTracker()
    tracker.add_transaction("2025-03-01", 50, "expense", "Food")
    summary = analytics.monthly_summary(analytics.to_dataframe(tracker.transactions))
    assert summary.loc["2025-03", "income"] == 0
    assert summary.loc["2025-03", "savings_rate"] == 0  # no division by zero


def test_category_breakdown(df: pd.DataFrame) -> None:
    breakdown = analytics.category_breakdown(df)
    assert list(breakdown["category"]) == ["Housing", "Groceries", "Dining Out"]
    assert breakdown["share"].sum() == pytest.approx(100, abs=0.05)
    assert breakdown.loc[breakdown["category"] == "Groceries", "count"].item() == 2
    income = analytics.category_breakdown(df, kind="income")
    assert list(income["category"]) == ["Salary", "Freelance"]


def test_spending_trend(df: pd.DataFrame) -> None:
    trend = analytics.spending_trend(df, window=2)
    assert list(trend["expense"]) == [1430.5, 1620.0]
    assert trend.loc["2025-02", "rolling_avg"] == pytest.approx(1525.25)
    assert math.isnan(trend.loc["2025-01", "mom_change_pct"])
    assert trend.loc["2025-02", "mom_change_pct"] == pytest.approx(13.25, abs=0.01)


def test_category_by_month_and_top_expenses(df: pd.DataFrame) -> None:
    table = analytics.category_by_month(df)
    assert table.loc["2025-01", "Dining Out"] == 80
    assert table.loc["2025-02", "Dining Out"] == 0  # filled, not missing
    top = analytics.top_expenses(df, n=3)
    assert list(top["amount"]) == [1200, 1200, 420]


def test_filter_dataframe(df: pd.DataFrame) -> None:
    feb = analytics.filter_dataframe(df, start="2025-02-01", end="2025-02-28")
    assert len(feb) == 4
    groceries = analytics.filter_dataframe(df, categories=["Groceries"])
    assert set(groceries["category"]) == {"Groceries"}


def test_kpis_and_savings_rate(df: pd.DataFrame) -> None:
    k = analytics.kpis(df)
    assert k["income"] == 6500
    assert k["expense"] == 3050.5
    assert k["net"] == 3449.5
    assert k["savings_rate"] == 53.1
    assert k["avg_monthly_expense"] == 1525.25
    assert k["transactions"] == 8


def test_empty_dataframe_is_handled() -> None:
    empty = analytics.to_dataframe([])
    assert empty.empty
    assert analytics.monthly_summary(empty).empty
    assert analytics.category_breakdown(empty).empty
    assert analytics.spending_trend(empty).empty
    assert analytics.category_by_month(empty).empty
    assert analytics.top_expenses(empty).empty
    assert analytics.savings_rate(empty) == 0.0
    assert analytics.kpis(empty)["avg_monthly_expense"] == 0.0


def test_trend_includes_months_without_expenses() -> None:
    tracker = FinanceTracker()
    tracker.add_transaction("2025-01-10", 100, "expense", "Food")
    tracker.add_transaction("2025-02-01", 900, "income", "Salary")  # no expense in Feb
    tracker.add_transaction("2025-04-10", 200, "expense", "Food")
    trend = analytics.spending_trend(analytics.to_dataframe(tracker.transactions))
    assert list(trend.index) == ["2025-01", "2025-02", "2025-03", "2025-04"]
    assert list(trend["expense"]) == [100, 0, 0, 200]
    assert trend.loc["2025-02", "mom_change_pct"] == -100
    assert math.isnan(trend.loc["2025-04", "mom_change_pct"])  # growth from $0
