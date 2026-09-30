"""Generate realistic, reproducible sample data for the finance tracker.

Creates about 300 transactions over 6 months for a fictional student with a
part-time job and freelance work, plus budgets and savings goals, then writes:
    data/sample_transactions.csv  (transactions only)
    data/sample_data.json         (transactions + budgets + goals)

The data is entirely fictional. A fixed random seed makes every run identical,
so tests, screenshots and the demo video always show the same numbers.

Usage:
    python tools/generate_sample_data.py [--seed 42] [--end 2026-09-30]
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from finance_tracker.config import SAMPLE_CSV, SAMPLE_JSON  # noqa: E402
from finance_tracker.tracker import FinanceTracker  # noqa: E402

DEFAULT_SEED = 42
DEFAULT_END = date(2026, 9, 30)
MONTHS = 6

# (category, description options, min amount, max amount, occurrences per month)
VARIABLE_EXPENSES: list[tuple[str, list[str], float, float, int]] = [
    ("Groceries", ["Safeway", "QFC", "Trader Joe's", "Costco run", "Farmers market"], 12, 75, 10),
    ("Dining Out", ["Coffee", "Lunch on campus", "Pho", "Pizza night", "Sushi"], 4, 30, 14),
    ("Transportation", ["Gas", "ORCA card reload", "Parking", "Uber"], 8, 55, 6),
    ("Entertainment", ["Movie ticket", "Concert", "Bowling", "Game purchase"], 10, 60, 4),
    ("Shopping", ["Clothes", "Amazon order", "Target", "Shoes"], 15, 100, 3),
    ("Health", ["Pharmacy", "Gym drop-in", "Vitamins"], 10, 50, 2),
]
# (day of month, category, description, amount)
FIXED_EXPENSES: list[tuple[int, str, str, float]] = [
    (1, "Housing", "Rent (shared apartment)", 950.00),
    (5, "Utilities", "Phone plan", 45.00),
    (12, "Utilities", "Internet (split)", 30.00),
    (15, "Entertainment", "Streaming subscriptions", 22.98),
    (20, "Utilities", "Electricity (split)", 38.00),
]


def month_starts(end: date, count: int) -> list[date]:
    """Return the first day of the ``count`` months ending with ``end``'s month."""
    starts: list[date] = []
    year, month = end.year, end.month
    for _ in range(count):
        starts.append(date(year, month, 1))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return sorted(starts)


def days_in_month(first: date) -> int:
    """Number of days in the month starting at ``first``."""
    next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    return (next_month - first).days


def build_tracker(seed: int = DEFAULT_SEED, end: date = DEFAULT_END) -> FinanceTracker:
    """Build a tracker filled with ~300 fictional transactions.

    Args:
        seed: Random seed for reproducibility.
        end: Last day covered by the data.

    Returns:
        The filled tracker, with budgets and savings goals.
    """
    rng = random.Random(seed)
    tracker = FinanceTracker()
    for index, first in enumerate(month_starts(end, MONTHS)):
        last_day = days_in_month(first)
        # Income: bi-weekly pay cheques plus occasional freelance work.
        for day in (1, 15):
            pay = round(rng.uniform(1450, 1550), 2)
            tracker.add_transaction(first.replace(day=day), pay, "income", "Salary", "Paycheck")
        if rng.random() < 0.7:
            tracker.add_transaction(
                first.replace(day=rng.randint(5, 25)),
                round(rng.uniform(150, 600), 2),
                "income",
                "Freelance",
                rng.choice(["Website project", "Tutoring", "Logo design"]),
            )
        for day, category, description, amount in FIXED_EXPENSES:
            tracker.add_transaction(
                first.replace(day=day), amount, "expense", category, description
            )
        # A holiday-like spike in month 4 makes the trend chart interesting.
        spike = 1.35 if index == 3 else 1.0
        for category, descriptions, low, high, per_month in VARIABLE_EXPENSES:
            for _ in range(per_month + rng.randint(-1, 2)):
                tracker.add_transaction(
                    first.replace(day=rng.randint(1, last_day)),
                    round(rng.uniform(low, high) * spike, 2),
                    "expense",
                    category,
                    rng.choice(descriptions),
                )
        if index in (1, 4):
            tracker.add_transaction(
                first.replace(day=rng.randint(3, 25)),
                round(rng.uniform(250, 420), 2),
                "expense",
                "Education",
                "Textbooks & course fees",
            )

    for category, limit in {
        "Groceries": 500,
        "Dining Out": 250,
        "Transportation": 180,
        "Entertainment": 150,
        "Shopping": 200,
        "Utilities": 120,
        "Housing": 1000,
    }.items():
        tracker.set_budget(category, limit)
    tracker.add_goal("Emergency Fund", 3000, saved=1850, deadline=date(2026, 12, 31))
    tracker.add_goal("New Laptop", 1400, saved=1050, deadline=date(2026, 11, 30))
    tracker.add_goal("Summer Trip", 2000, saved=400, deadline=date(2027, 6, 1))
    return tracker


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--end", type=date.fromisoformat, default=DEFAULT_END)
    parser.add_argument("--csv", type=Path, default=SAMPLE_CSV)
    parser.add_argument("--json", type=Path, default=SAMPLE_JSON)
    args = parser.parse_args(argv)

    tracker = build_tracker(args.seed, args.end)
    tracker.export_csv(args.csv)
    tracker.save_json(args.json)
    print(
        f"Generated {len(tracker.transactions)} transactions "
        f"({tracker.months()[0]} → {tracker.months()[-1]})"
    )
    print(f"  CSV : {args.csv}")
    print(f"  JSON: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
