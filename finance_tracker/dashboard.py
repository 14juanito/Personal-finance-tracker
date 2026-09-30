"""Interactive Streamlit dashboard.

Run with:
    streamlit run finance_tracker/dashboard.py

Main elements:
    Sidebar: data source (sample data, your saved data, or an uploaded CSV/JSON file),
        date range, category and kind filters.
    KPI row: income, expenses, net, savings rate, average monthly spending, with the
        change versus the previous month.
    Tabs: Overview, Trends, Budgets & Alerts, Savings Goals, Transactions (with CSV download).

Course concepts illustrated:
    - pandas: every table and chart is computed with ``analytics`` (groupby, pivot, rolling).
    - Functions: the page is split into one function per section.
    - File handling and exceptions: uploaded files are validated; bad files show an error.
    - Decisions: filters and data-source choice change what is computed.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

# `streamlit run` executes this file as a script, so only this folder is on sys.path;
# add the project root to make `import finance_tracker` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from finance_tracker import alerts, analytics  # noqa: E402
from finance_tracker.config import SAMPLE_JSON, USER_DATA_FILE  # noqa: E402
from finance_tracker.exceptions import FinanceTrackerError  # noqa: E402
from finance_tracker.models import EXPENSE, INCOME  # noqa: E402
from finance_tracker.tracker import FinanceTracker  # noqa: E402

PAGE_TITLE = "Personal Finance Dashboard"
INCOME_COLOR = "#2E7D32"
EXPENSE_COLOR = "#C62828"
ACCENT_COLOR = "#1565C0"
LEVEL_ICONS = {"EXCEEDED": "🔴", "WARNING": "🟠", "OK": "🟢", "INFO": "🔵"}
SOURCE_SAMPLE = "Sample data"
SOURCE_SAVED = "My saved data"
SOURCE_UPLOAD = "Upload a file"


@st.cache_data(show_spinner=False)
def load_from_path(path: str, _mtime: float) -> tuple[FinanceTracker, list[str]]:
    """Load a JSON data file (cached until the file changes).

    Args:
        path: JSON file to read.
        _mtime: File modification time — part of the cache key so edits are picked up.

    Returns:
        ``(tracker, warnings)``.

    Raises:
        StorageError: If the file is corrupted. The dashboard only *views* data, so it
            reports the problem instead of renaming the user's file.
    """
    return FinanceTracker.load_json(path, recover=False)


def load_upload(name: str, content: bytes) -> tuple[FinanceTracker, list[str]]:
    """Load an uploaded CSV or JSON file through the normal storage code.

    Args:
        name: Original file name (its extension selects the parser).
        content: Raw bytes of the uploaded file.

    Returns:
        ``(tracker, warnings)`` — invalid rows are skipped and listed in ``warnings``.

    Raises:
        FinanceTrackerError: If the file cannot be parsed.
    """
    suffix = Path(name).suffix.lower()
    # Concept: file handling — the upload is written to a temporary folder that is
    # deleted automatically, then parsed by the same code as local files.
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / f"upload{suffix}"
        path.write_bytes(content)
        if suffix == ".csv":
            return FinanceTracker.from_csv(path)
        # A broken upload must be reported, not silently replaced by empty data.
        return FinanceTracker.load_json(path, recover=False)


def choose_data() -> tuple[FinanceTracker, str] | None:
    """Sidebar: pick the data source and load it.

    Returns:
        ``(tracker, label)`` for the chosen source, or None when nothing could be
        loaded (an explanation is already shown on the page).
    """
    st.sidebar.header("Data")
    options = [SOURCE_SAMPLE, SOURCE_UPLOAD]
    if USER_DATA_FILE.exists():
        options.insert(0, SOURCE_SAVED)
    source = st.sidebar.radio("Source", options, label_visibility="collapsed")
    try:
        if source == SOURCE_UPLOAD:
            upload = st.sidebar.file_uploader("CSV or JSON file", type=["csv", "json"])
            if upload is None:
                st.info("Upload a CSV (date, amount, kind, category, description) or JSON file.")
                return None
            tracker, warnings = load_upload(upload.name, upload.getvalue())
            label = upload.name
        else:
            path = USER_DATA_FILE if source == SOURCE_SAVED else SAMPLE_JSON
            if not path.exists():
                st.error(f"Data file not found: {path.name}")
                return None
            tracker, warnings = load_from_path(str(path), path.stat().st_mtime)
            label = path.name
    except FinanceTrackerError as exc:
        st.error(f"Could not load the file: {exc}")
        return None
    for warning in warnings[:5]:
        st.sidebar.warning(warning)
    return tracker, label


def sidebar_filters(df: pd.DataFrame) -> tuple[date, date, list[str], str]:
    """Sidebar: date range, categories and kind.

    Args:
        df: The full DataFrame, used for the available dates and categories.

    Returns:
        ``(start, end, categories, kind)`` where kind is "All", "Expenses" or "Income".
    """
    st.sidebar.header("Filters")
    first, last = df["date"].min().date(), df["date"].max().date()
    picked = st.sidebar.date_input("Date range", (first, last), min_value=first, max_value=last)
    # While the user is choosing, date_input returns a 1-tuple; fall back to the full range.
    start, end = picked if isinstance(picked, tuple) and len(picked) == 2 else (first, last)
    categories = sorted(df["category"].unique())
    chosen = st.sidebar.multiselect("Categories", categories, default=categories)
    kind = st.sidebar.radio("Show", ["All", "Expenses", "Income"], horizontal=True)
    return start, end, chosen, kind


def md_escape(text: str) -> str:
    """Escape "$" so Markdown does not render the text between two amounts as math.

    Args:
        text: Plain text that may contain dollar amounts.

    Returns:
        The text with every ``$`` written as ``\\$``.
    """
    return text.replace("$", "\\$")


def signed_money(amount: float) -> str:
    """Format a change as ``+$1,234`` or ``-$56``.

    Args:
        amount: The change to format.

    Returns:
        The signed, rounded dollar amount.
    """
    return f"{'-' if amount < 0 else '+'}${abs(amount):,.0f}"


def kpi_row(df: pd.DataFrame) -> None:
    """Headline metrics with the change versus the previous month.

    Args:
        df: Filtered DataFrame.
    """
    k = analytics.kpis(df)
    summary = analytics.monthly_summary(df)
    delta_expense = delta_net = None
    if len(summary) >= 2:
        last, previous = summary.iloc[-1], summary.iloc[-2]
        delta_expense = f"{signed_money(last['expense'] - previous['expense'])} vs prev. month"
        delta_net = f"{signed_money(last['net'] - previous['net'])} vs prev. month"
    cols = st.columns(5)
    cols[0].metric("Income", f"${k['income']:,.0f}")
    cols[1].metric("Expenses", f"${k['expense']:,.0f}", delta_expense, delta_color="inverse")
    cols[2].metric("Net savings", f"${k['net']:,.0f}", delta_net)
    # Without income in the selection (e.g. "Expenses" only) a rate is meaningless.
    has_income = k["income"] > 0
    cols[3].metric("Savings rate", f"{k['savings_rate']:.1f}%" if has_income else "n/a")
    cols[4].metric("Avg. spend / month", f"${k['avg_monthly_expense']:,.0f}")


def overview_tab(df: pd.DataFrame) -> None:
    """Monthly income vs. expenses and category breakdown.

    Args:
        df: Filtered DataFrame.
    """
    summary = analytics.monthly_summary(df).reset_index()
    left, right = st.columns([3, 2])
    with left:
        fig = go.Figure()
        fig.add_bar(
            x=summary["month"], y=summary["income"], name="Income", marker_color=INCOME_COLOR
        )
        fig.add_bar(
            x=summary["month"], y=summary["expense"], name="Expenses", marker_color=EXPENSE_COLOR
        )
        fig.add_scatter(
            x=summary["month"],
            y=summary["net"],
            name="Net",
            mode="lines+markers",
            line={"color": ACCENT_COLOR},
        )
        fig.update_layout(
            title="Monthly income vs. expenses",
            barmode="group",
            yaxis_tickprefix="$",
            legend={"orientation": "h", "y": -0.15},
            margin={"t": 50, "b": 10},
        )
        st.plotly_chart(fig, width="stretch")
    with right:
        breakdown = analytics.category_breakdown(df)
        if breakdown.empty:
            st.info("No expenses in the selection.")
        else:
            fig = px.pie(
                breakdown, names="category", values="total", hole=0.5, title="Expenses by category"
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(showlegend=False, margin={"t": 50, "b": 10})
            st.plotly_chart(fig, width="stretch")
    st.dataframe(
        summary.rename(columns=str.title),
        hide_index=True,
        width="stretch",
        column_config={
            c: st.column_config.NumberColumn(format="dollar") for c in ("Income", "Expense", "Net")
        }
        | {"Savings_Rate": st.column_config.NumberColumn("Savings rate", format="%.1f%%")},
    )


def trends_tab(df: pd.DataFrame) -> None:
    """Rolling-average trend line, month x category heatmap and top expenses.

    Args:
        df: Filtered DataFrame.
    """
    trend = analytics.spending_trend(df).reset_index()
    if trend.empty:
        st.info("No expenses in the selection.")
        return
    fig = go.Figure()
    fig.add_scatter(
        x=trend["month"],
        y=trend["expense"],
        name="Monthly expenses",
        mode="lines+markers",
        line={"color": EXPENSE_COLOR},
        customdata=trend["mom_change_pct"],
        hovertemplate="%{x}: $%{y:,.0f}<br>MoM: %{customdata:+.1f}%<extra></extra>",
    )
    fig.add_scatter(
        x=trend["month"],
        y=trend["rolling_avg"],
        name=f"{analytics.DEFAULT_TREND_WINDOW}-month average",
        line={"dash": "dash", "color": ACCENT_COLOR},
    )
    fig.update_layout(title="Spending trend", yaxis_tickprefix="$", margin={"t": 50})
    st.plotly_chart(fig, width="stretch")

    table = analytics.category_by_month(df)
    heat = px.imshow(
        table.T,
        text_auto=".0f",
        aspect="auto",
        color_continuous_scale="Reds",
        title="Spending by category and month ($)",
        labels={"x": "Month", "y": "Category", "color": "$"},
    )
    st.plotly_chart(heat, width="stretch")
    st.subheader("Top 10 expenses")
    top = analytics.top_expenses(df, 10)
    top["date"] = top["date"].dt.date
    st.dataframe(
        top,
        hide_index=True,
        width="stretch",
        column_config={"amount": st.column_config.NumberColumn(format="dollar")},
    )


def budgets_tab(tracker: FinanceTracker) -> None:
    """Budget usage for a chosen month, with alert levels.

    Args:
        tracker: The loaded data (budgets are monthly, so filters do not apply).
    """
    months = tracker.months()
    if not tracker.budgets or not months:
        st.info("No budgets defined for this data.")
        return
    st.caption("Budgets are monthly, so this tab uses the whole dataset, not the sidebar filters.")
    month = st.selectbox("Month", months[::-1])
    for alert in alerts.check_budgets(tracker, month, include_ok=True):
        st.markdown(f"{LEVEL_ICONS[alert.level]} **{alert.level}** — {md_escape(alert.message)}")
        st.progress(min(alert.ratio, 1.0))


def goals_tab(tracker: FinanceTracker) -> None:
    """Savings goal progress and milestones.

    Args:
        tracker: The loaded data.
    """
    if not tracker.goals:
        st.info("No savings goals in this data.")
        return
    st.caption("Goals track saved money, not transactions: the sidebar filters do not apply.")
    cols = st.columns(len(tracker.goals))
    for col, goal in zip(cols, tracker.goals.values(), strict=True):
        with col:
            st.metric(
                goal.name, f"${goal.saved:,.0f}", f"{goal.progress:.0%} of ${goal.target:,.0f}"
            )
            st.progress(goal.progress)
            deadline = goal.deadline.isoformat() if goal.deadline else "no deadline"
            st.caption(f"${goal.remaining:,.0f} to go · {deadline}")
    for alert in alerts.check_goals(tracker):
        st.markdown(f"{LEVEL_ICONS[alert.level]} {md_escape(alert.message)}")


def transactions_tab(df: pd.DataFrame) -> None:
    """Filtered transaction table with a CSV download button.

    Args:
        df: Filtered DataFrame.
    """
    shown = df.sort_values("date", ascending=False)[
        ["date", "kind", "category", "amount", "description"]
    ].copy()
    shown["date"] = shown["date"].dt.date
    st.dataframe(
        shown,
        hide_index=True,
        width="stretch",
        height=420,
        column_config={"amount": st.column_config.NumberColumn(format="dollar")},
    )
    st.download_button(
        "Download CSV",
        shown.to_csv(index=False).encode("utf-8"),
        file_name="filtered_transactions.csv",
        mime="text/csv",
    )


def main() -> None:
    """Build the whole page."""
    st.set_page_config(page_title=PAGE_TITLE, page_icon="💰", layout="wide")
    st.title("💰 Personal Finance Dashboard")
    loaded = choose_data()
    if loaded is None:
        return
    tracker, label = loaded
    df_all = analytics.to_dataframe(tracker.transactions)
    if df_all.empty:
        st.warning("This file contains no transactions.")
        return
    start, end, categories, kind = sidebar_filters(df_all)
    # Concept: pandas — the sidebar filters become boolean masks on the DataFrame
    df = analytics.filter_dataframe(df_all, start, end, categories)
    if kind == "Expenses":
        df = df[df["kind"] == EXPENSE]
    elif kind == "Income":
        df = df[df["kind"] == INCOME]
    st.caption(f"{label} · {start} → {end} · {len(df)} of {len(df_all)} transactions")
    if df.empty:
        st.warning("No transactions match the filters.")
        return
    kpi_row(df)
    tabs = st.tabs(["Overview", "Trends", "Budgets & Alerts", "Savings Goals", "Transactions"])
    with tabs[0]:
        overview_tab(df)
    with tabs[1]:
        trends_tab(df)
    with tabs[2]:
        budgets_tab(tracker)
    with tabs[3]:
        goals_tab(tracker)
    with tabs[4]:
        transactions_tab(df)


main()
