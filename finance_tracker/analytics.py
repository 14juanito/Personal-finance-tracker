"""Spending analysis with pandas.

Main elements:
    to_dataframe: convert transactions into a typed pandas DataFrame.
    monthly_summary: income, expenses, net and savings rate per month.
    category_breakdown: totals, share and count per category.
    spending_trend: monthly expenses with a rolling average and month-over-month change.
    category_by_month: pivot table month x category.
    top_expenses: the largest individual expenses.
    savings_rate / kpis: headline numbers for dashboards.

Every function accepts an empty DataFrame and returns an empty (but well-formed)
result, so the UIs never have to special-case "no data yet".

Course concepts illustrated:
    - pandas: DataFrame construction, dtypes, groupby, pivot_table, rolling,
      pct_change, nlargest, boolean filtering.
    - Functions: each analysis is a small, reusable, testable function.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from finance_tracker.models import EXPENSE, INCOME, Transaction

COLUMNS: list[str] = ["id", "date", "amount", "kind", "category", "description"]
DEFAULT_TREND_WINDOW = 3


def to_dataframe(transactions: Iterable[Transaction]) -> pd.DataFrame:
    """Build a DataFrame from transactions.

    Args:
        transactions: Any iterable of ``Transaction`` objects.

    Returns:
        A DataFrame sorted by date with columns ``id, date, amount, kind, category,
        description, signed_amount, month``. ``date`` is ``datetime64`` and ``month``
        is a ``YYYY-MM`` string.
    """
    # Concept: pandas — create a DataFrame from a list of dictionaries
    df = pd.DataFrame([t.to_dict() for t in transactions], columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float)
    # Vectorised: one expression for the whole column instead of a Python loop.
    df["signed_amount"] = df["amount"].where(df["kind"] == INCOME, -df["amount"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    return df.sort_values("date", ignore_index=True)


def filter_dataframe(
    df: pd.DataFrame,
    start: pd.Timestamp | str | None = None,
    end: pd.Timestamp | str | None = None,
    categories: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Keep rows within a date range and/or a set of categories.

    Args:
        df: DataFrame from ``to_dataframe``.
        start: First date included.
        end: Last date included.
        categories: Categories to keep; None keeps all.

    Returns:
        The filtered DataFrame (a new object).
    """
    # Concept: pandas — boolean masks combine several conditions without loops
    mask = pd.Series(True, index=df.index)
    if start is not None:
        mask &= df["date"] >= pd.Timestamp(start)
    if end is not None:
        mask &= df["date"] <= pd.Timestamp(end)
    if categories is not None:
        mask &= df["category"].isin(list(categories))
    return df.loc[mask].copy()


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Income, expenses, net and savings rate for each month.

    Args:
        df: DataFrame from ``to_dataframe``.

    Returns:
        DataFrame indexed by ``month`` with columns ``income``, ``expense``, ``net``
        and ``savings_rate`` (net / income, in %; 0 when there is no income).
    """
    columns = ["income", "expense", "net", "savings_rate"]
    if df.empty:
        return pd.DataFrame(columns=columns, index=pd.Index([], name="month"), dtype=float)
    # Concept: pandas — group expenses by month and kind, then pivot kinds into columns
    summary = df.pivot_table(
        index="month", columns="kind", values="amount", aggfunc="sum", fill_value=0.0
    )
    summary = summary.reindex(columns=[INCOME, EXPENSE], fill_value=0.0)
    summary.columns = ["income", "expense"]
    summary["net"] = summary["income"] - summary["expense"]
    income = summary["income"].where(summary["income"] > 0)
    summary["savings_rate"] = (summary["net"] / income * 100).fillna(0.0)
    summary.columns.name = None
    return summary.round(2)


def category_breakdown(df: pd.DataFrame, kind: str = EXPENSE) -> pd.DataFrame:
    """Totals per category for one kind of transaction.

    Args:
        df: DataFrame from ``to_dataframe``.
        kind: ``"expense"`` (default) or ``"income"``.

    Returns:
        DataFrame with columns ``category``, ``total``, ``share`` (% of the kind's
        total) and ``count``, sorted by ``total`` descending.
    """
    subset = df[df["kind"] == kind]
    if subset.empty:
        return pd.DataFrame(columns=["category", "total", "share", "count"])
    # Concept: pandas — groupby + named aggregation computes several stats at once
    grouped = (
        subset.groupby("category")
        .agg(total=("amount", "sum"), count=("amount", "size"))
        .sort_values("total", ascending=False)
        .reset_index()
    )
    grouped["share"] = grouped["total"] / grouped["total"].sum() * 100
    return grouped[["category", "total", "share", "count"]].round(2)


def spending_trend(df: pd.DataFrame, window: int = DEFAULT_TREND_WINDOW) -> pd.DataFrame:
    """Monthly expenses with a rolling average and month-over-month change.

    Args:
        df: DataFrame from ``to_dataframe``.
        window: Number of months in the rolling average.

    Returns:
        DataFrame indexed by every calendar month between the first and last
        transaction, with ``expense``, ``rolling_avg`` (average of up to ``window``
        months — the first months use the ones available) and ``mom_change_pct``
        (NaN for the first month, which has no predecessor).
    """
    expenses = df[df["kind"] == EXPENSE]
    if expenses.empty:
        return pd.DataFrame(
            columns=["expense", "rolling_avg", "mom_change_pct"],
            index=pd.Index([], name="month"),
            dtype=float,
        )
    trend = expenses.groupby("month")["amount"].sum().to_frame("expense")
    # A month with no expenses must still count as a month (with 0 spent); otherwise
    # "month over month" could silently compare January with April.
    all_months = pd.period_range(df["month"].min(), df["month"].max(), freq="M")
    trend = trend.reindex(all_months.strftime("%Y-%m"), fill_value=0.0)
    trend.index.name = "month"
    # Concept: pandas — rolling window smooths out one-off spikes in spending
    trend["rolling_avg"] = trend["expense"].rolling(window=window, min_periods=1).mean()
    change = trend["expense"].pct_change() * 100
    # Growth from a $0 month is infinite, which is meaningless to display.
    trend["mom_change_pct"] = change.replace([float("inf"), float("-inf")], float("nan"))
    return trend.round(2)


def category_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Expense totals as a month x category table.

    Args:
        df: DataFrame from ``to_dataframe``.

    Returns:
        Pivot table indexed by month, one column per category, missing
        combinations filled with 0 (empty DataFrame when there are no expenses).
    """
    expenses = df[df["kind"] == EXPENSE]
    if expenses.empty:
        return pd.DataFrame()
    table = expenses.pivot_table(
        index="month", columns="category", values="amount", aggfunc="sum", fill_value=0.0
    )
    table.columns.name = None
    return table.round(2)


def top_expenses(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """The ``n`` largest single expenses.

    Args:
        df: DataFrame from ``to_dataframe``.
        n: Number of rows to return.

    Returns:
        DataFrame with ``date``, ``category``, ``description`` and ``amount``.
    """
    expenses = df[df["kind"] == EXPENSE]
    return expenses.nlargest(n, "amount")[["date", "category", "description", "amount"]]


def savings_rate(df: pd.DataFrame) -> float:
    """Overall savings rate in % ((income - expenses) / income).

    Args:
        df: DataFrame from ``to_dataframe``.

    Returns:
        The rate rounded to 1 decimal, or 0.0 when there is no income.
    """
    income = df.loc[df["kind"] == INCOME, "amount"].sum()
    expense = df.loc[df["kind"] == EXPENSE, "amount"].sum()
    if income <= 0:
        return 0.0
    return round(float((income - expense) / income * 100), 1)


def kpis(df: pd.DataFrame) -> dict[str, float]:
    """Headline numbers for dashboards.

    Args:
        df: DataFrame from ``to_dataframe``.

    Returns:
        Dict with ``income``, ``expense``, ``net``, ``savings_rate``,
        ``avg_monthly_expense`` and ``transactions`` (all as floats).
    """
    income = float(df.loc[df["kind"] == INCOME, "amount"].sum())
    expense = float(df.loc[df["kind"] == EXPENSE, "amount"].sum())
    months = df["month"].nunique()
    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "net": round(income - expense, 2),
        "savings_rate": savings_rate(df),
        "avg_monthly_expense": round(expense / months, 2) if months else 0.0,
        "transactions": float(len(df)),
    }
