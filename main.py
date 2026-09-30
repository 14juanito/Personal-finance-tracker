"""Entry point of the Personal Finance Tracker.

Usage:
    python main.py cli     Interactive console menu.
    python main.py gui     Tkinter desktop interface.
    python main.py demo    Non-interactive walkthrough on the sample data: summaries,
                           alerts, pandas analysis, charts and file exports.

    streamlit run finance_tracker/dashboard.py    Interactive web dashboard.

Options:
    --data PATH     JSON data file (cli/gui: your data; demo: the dataset to analyse).
    --output DIR    Folder for demo charts and exports (default: output/).

Course concepts illustrated:
    - Functions: ``main`` dispatches to one function per mode.
    - Decision structures: choosing the mode from the command-line argument.
    - User output: a formatted, readable text report in demo mode.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from finance_tracker import alerts, analytics, visualize
from finance_tracker.cli import format_money, format_table
from finance_tracker.config import OUTPUT_DIR, SAMPLE_JSON, USER_DATA_FILE
from finance_tracker.tracker import FinanceTracker

MODES: tuple[str, ...] = ("cli", "gui", "demo")


def run_demo(
    data_file: Path = SAMPLE_JSON,
    out_dir: Path = OUTPUT_DIR,
    output_func: Callable[[str], None] = print,
) -> list[Path]:
    """Run every feature once, without asking the user anything.

    Args:
        data_file: JSON dataset to analyse.
        out_dir: Folder receiving ``charts/*.png`` and the JSON/CSV exports.
        output_func: Where to write the report (``print`` by default).

    Returns:
        Paths of all files written.
    """
    out = output_func

    def section(title: str) -> None:
        out("")
        out(f"── {title} ".ljust(72, "─"))

    tracker, warnings = FinanceTracker.load_json(data_file)
    for warning in warnings:
        out(f"⚠ {warning}")
    df = analytics.to_dataframe(tracker.transactions)
    months = tracker.months()

    out("PERSONAL FINANCE TRACKER — DEMO")
    out(f"Dataset: {Path(data_file).name}  |  {len(tracker.transactions)} transactions")
    if months:
        used = {t.category for t in tracker.transactions}
        out(f"Period:  {months[0]} → {months[-1]}  |  {len(used)} categories used")

    section("1. Overall summary")
    k = analytics.kpis(df)
    out(f"Total income     {format_money(k['income']):>14}")
    out(f"Total expenses   {format_money(k['expense']):>14}")
    out(f"Net savings      {format_money(k['net']):>14}")
    out(f"Savings rate     {k['savings_rate']:>13.1f}%")
    out(f"Avg. spend/month {format_money(k['avg_monthly_expense']):>14}")

    section("2. Monthly summary (pandas pivot table)")
    summary = analytics.monthly_summary(df)
    out(
        format_table(
            ["Month", "Income", "Expenses", "Net", "Savings rate"],
            [
                [
                    month,
                    format_money(row["income"]),
                    format_money(row["expense"]),
                    format_money(row["net"]),
                    f"{row['savings_rate']:.1f}%",
                ]
                for month, row in summary.iterrows()
            ],
        )
    )

    section("3. Spending by category (pandas groupby)")
    breakdown = analytics.category_breakdown(df)
    out(
        format_table(
            ["Category", "Total", "Share", "Count"],
            [
                [r.category, format_money(r.total), f"{r.share:.1f}%", r.count]
                for r in breakdown.itertuples()
            ],
        )
    )

    section("4. Spending trend (3-month rolling average, month-over-month %)")
    trend = analytics.spending_trend(df)
    out(
        format_table(
            ["Month", "Expenses", "3-mo avg", "MoM change"],
            [
                [
                    month,
                    format_money(row["expense"]),
                    format_money(row["rolling_avg"]),
                    "-" if row.isna()["mom_change_pct"] else f"{row['mom_change_pct']:+.1f}%",
                ]
                for month, row in trend.iterrows()
            ],
        )
    )

    section("5. Top 5 expenses")
    out(
        format_table(
            ["Date", "Category", "Description", "Amount"],
            [
                [r.date.date().isoformat(), r.category, r.description, format_money(r.amount)]
                for r in analytics.top_expenses(df, 5).itertuples()
            ],
        )
    )

    latest = tracker.latest_month()
    section(f"6. Budget alerts for {latest}")
    budget_alerts = alerts.check_budgets(tracker, latest, include_ok=True)
    for alert in budget_alerts or []:
        out(f"  {alert}")
    if not budget_alerts:
        out("  No budgets defined.")

    section("7. Savings goals")
    for goal in tracker.goals.values():
        bar = "█" * round(goal.progress * 20)
        out(
            f"  {goal.name:<16} {bar:<20} {goal.progress:>4.0%}  "
            f"{format_money(goal.saved)} / {format_money(goal.target)}"
        )
    for alert in alerts.check_goals(tracker):
        out(f"  {alert}")

    section("8. Files written")
    out_dir = Path(out_dir)
    written = visualize.save_all_charts(df, tracker.goals.values(), out_dir / "charts")
    written.append(tracker.save_json(out_dir / "demo_data.json"))
    written.append(tracker.export_csv(out_dir / "demo_transactions.csv"))
    for path in written:
        out(f"  ✓ {path}")
    out("\nDemo complete.")
    return written


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Personal Finance Tracker — DATA 333, Bellevue College",
        epilog="Dashboard: streamlit run finance_tracker/dashboard.py",
    )
    parser.add_argument("mode", choices=MODES, help="cli, gui or demo")
    parser.add_argument("--data", type=Path, default=None, help="JSON data file")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR, help="demo output folder")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and launch the requested mode.

    Returns:
        Process exit code (0 = success).
    """
    args = build_parser().parse_args(argv)
    # Symbols such as "✓" or "█" cannot be encoded by some Windows consoles; replace
    # them with "?" instead of crashing with UnicodeEncodeError.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    # Concept: decision structure — one branch per execution mode
    if args.mode == "cli":
        from finance_tracker import cli

        cli.run(args.data or USER_DATA_FILE)
    elif args.mode == "gui":
        # Imported lazily so that cli/demo work even where Tk is not installed.
        from finance_tracker import gui_tkinter

        gui_tkinter.run(args.data or USER_DATA_FILE)
    else:
        data_file = args.data or SAMPLE_JSON
        if not data_file.exists():
            print(f"Error: data file not found: {data_file}", file=sys.stderr)
            return 1
        run_demo(data_file, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
