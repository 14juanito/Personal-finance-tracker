"""Charts built with matplotlib and saved as PNG files.

Main elements:
    category_pie: share of expenses per category.
    monthly_bars: income vs. expenses side by side for each month.
    trend_line: monthly expenses with a rolling average.
    goals_progress: horizontal progress bars for savings goals.
    save_all_charts: render every chart into ``output/charts/``.

Design note: figures are created with ``matplotlib.figure.Figure`` instead of
``pyplot``. This needs no GUI backend (works headless in demo mode and tests) and the
very same Figure objects can be embedded in the Tkinter window.

Course concepts illustrated:
    - Functions: one function per chart, each returning a Figure.
    - pandas: charts are fed by the DataFrames from ``analytics``.
    - File handling: saving images into a folder created on demand.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from finance_tracker import analytics
from finance_tracker.config import CHARTS_DIR
from finance_tracker.models import SavingsGoal

INCOME_COLOR = "#2E7D32"
EXPENSE_COLOR = "#C62828"
ACCENT_COLOR = "#1565C0"
MUTED_COLOR = "#9E9E9E"
PALETTE: list[str] = [
    "#1565C0",
    "#EF6C00",
    "#2E7D32",
    "#6A1B9A",
    "#C62828",
    "#00838F",
    "#AD1457",
    "#9E9E9E",
]
MAX_PIE_SLICES = 7
FIGSIZE: tuple[float, float] = (8, 5)
DPI = 120

_money = FuncFormatter(lambda value, _pos: f"${value:,.0f}")


def _empty_figure(title: str, message: str = "No data to display", dpi: float = DPI) -> Figure:
    """Return a figure that shows a message instead of an empty plot."""
    fig = Figure(figsize=FIGSIZE, dpi=dpi)
    ax = fig.add_subplot()
    ax.set_title(title)
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=13, color=MUTED_COLOR)
    ax.set_axis_off()
    return fig


def category_pie(df: pd.DataFrame, title: str = "Expenses by Category", dpi: float = DPI) -> Figure:
    """Pie chart of expenses per category.

    Small categories beyond ``MAX_PIE_SLICES - 1`` are merged into one slice so the
    labels stay readable.

    Args:
        df: DataFrame from ``analytics.to_dataframe``.
        title: Chart title.
        dpi: Resolution; the GUI passes the screen's dpi so text stays readable.

    Returns:
        The matplotlib Figure.
    """
    breakdown = analytics.category_breakdown(df)
    if breakdown.empty:
        return _empty_figure(title, dpi=dpi)
    totals = breakdown.set_index("category")["total"]
    if len(totals) > MAX_PIE_SLICES:
        head = totals.iloc[: MAX_PIE_SLICES - 1]
        rest = pd.Series({"All others": totals.iloc[MAX_PIE_SLICES - 1 :].sum()})
        totals = pd.concat([head, rest])

    fig = Figure(figsize=FIGSIZE, dpi=dpi)
    ax = fig.add_subplot()
    wedges, _texts, _autotexts = ax.pie(
        totals.values,
        autopct="%1.0f%%",
        startangle=90,
        counterclock=False,
        pctdistance=0.78,
        colors=PALETTE[: len(totals)],
        wedgeprops={"width": 0.45, "edgecolor": "white"},  # donut: easier to compare
        textprops={"color": "white", "fontsize": 9, "weight": "bold"},
    )
    ax.legend(
        wedges,
        [f"{name}  ${value:,.0f}" for name, value in totals.items()],
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        frameon=False,
    )
    ax.text(0, 0, f"${totals.sum():,.0f}\ntotal", ha="center", va="center", fontsize=12)
    ax.set_title(title, weight="bold")
    ax.axis("equal")
    fig.tight_layout()
    return fig


def monthly_bars(
    df: pd.DataFrame, title: str = "Monthly Income vs. Expenses", dpi: float = DPI
) -> Figure:
    """Grouped bar chart of income and expenses per month.

    Args:
        df: DataFrame from ``analytics.to_dataframe``.
        title: Chart title.
        dpi: Resolution; the GUI passes the screen's dpi so text stays readable.

    Returns:
        The matplotlib Figure.
    """
    summary = analytics.monthly_summary(df)
    if summary.empty:
        return _empty_figure(title, dpi=dpi)
    positions = range(len(summary))
    width = 0.38
    fig = Figure(figsize=FIGSIZE, dpi=dpi)
    ax = fig.add_subplot()
    ax.bar(
        [p - width / 2 for p in positions],
        summary["income"],
        width,
        label="Income",
        color=INCOME_COLOR,
    )
    ax.bar(
        [p + width / 2 for p in positions],
        summary["expense"],
        width,
        label="Expenses",
        color=EXPENSE_COLOR,
    )
    ax.set_xticks(list(positions), summary.index)
    ax.yaxis.set_major_formatter(_money)
    ax.set_title(title, weight="bold")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def trend_line(df: pd.DataFrame, title: str = "Spending Trend", dpi: float = DPI) -> Figure:
    """Line chart of monthly expenses with a rolling average.

    Args:
        df: DataFrame from ``analytics.to_dataframe``.
        title: Chart title.
        dpi: Resolution; the GUI passes the screen's dpi so text stays readable.

    Returns:
        The matplotlib Figure.
    """
    trend = analytics.spending_trend(df)
    if trend.empty:
        return _empty_figure(title, dpi=dpi)
    fig = Figure(figsize=FIGSIZE, dpi=dpi)
    ax = fig.add_subplot()
    ax.plot(trend.index, trend["expense"], marker="o", color=EXPENSE_COLOR, label="Expenses")
    ax.plot(
        trend.index,
        trend["rolling_avg"],
        linestyle="--",
        color=ACCENT_COLOR,
        label=f"{analytics.DEFAULT_TREND_WINDOW}-month average",
    )
    # Label each point with its month-over-month change so the trend reads at a glance.
    for month, row in trend.iterrows():
        if pd.notna(row["mom_change_pct"]):
            ax.annotate(
                f"{row['mom_change_pct']:+.0f}%",
                (month, row["expense"]),
                textcoords="offset points",
                # Rises are labelled above the point, drops below, to keep clear of the line.
                xytext=(0, 8 if row["mom_change_pct"] >= 0 else -14),
                ha="center",
                fontsize=8,
                color=MUTED_COLOR,
            )
    ax.yaxis.set_major_formatter(_money)
    ax.set_title(title, weight="bold")
    ax.legend(frameon=False)
    ax.grid(alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def goals_progress(
    goals: Iterable[SavingsGoal], title: str = "Savings Goals", dpi: float = DPI
) -> Figure:
    """Horizontal bars showing how far each savings goal has progressed.

    Args:
        goals: Savings goals to display.
        title: Chart title.
        dpi: Resolution; the GUI passes the screen's dpi so text stays readable.

    Returns:
        The matplotlib Figure.
    """
    goals = list(goals)
    if not goals:
        return _empty_figure(title, "No savings goals yet", dpi)
    fig = Figure(figsize=FIGSIZE, dpi=dpi)
    ax = fig.add_subplot()
    names = [g.name for g in goals]
    progress = [g.progress * 100 for g in goals]
    ax.barh(names, [100] * len(goals), color="#E0E0E0")
    ax.barh(
        names,
        progress,
        color=[INCOME_COLOR if g.is_complete else ACCENT_COLOR for g in goals],
    )
    for index, goal in enumerate(goals):
        ax.text(
            101,
            index,
            # Escaped "$": two bare "$" signs would switch matplotlib into math-text mode.
            f"{goal.progress:.0%}  (\\${goal.saved:,.0f} / \\${goal.target:,.0f})",
            va="center",
            fontsize=9,
        )
    ax.set_xlim(0, 150)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("% of target")
    ax.invert_yaxis()
    ax.set_title(title, weight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def save_figure(fig: Figure, path: Path) -> Path:
    """Save a figure as PNG, creating the folder if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    return path


def save_all_charts(
    df: pd.DataFrame, goals: Iterable[SavingsGoal], out_dir: Path = CHARTS_DIR
) -> list[Path]:
    """Render every chart to PNG files.

    Args:
        df: DataFrame from ``analytics.to_dataframe``.
        goals: Savings goals for the progress chart.
        out_dir: Destination folder (created if missing).

    Returns:
        Paths of the files written.
    """
    # Concept: dictionary — map each output file name to the function that draws it
    charts = {
        "category_pie.png": category_pie(df),
        "monthly_income_expenses.png": monthly_bars(df),
        "spending_trend.png": trend_line(df),
        "goals_progress.png": goals_progress(goals),
    }
    return [save_figure(fig, Path(out_dir) / name) for name, fig in charts.items()]
