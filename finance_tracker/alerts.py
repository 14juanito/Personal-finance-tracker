"""Budget alerts and savings-goal milestones.

Main elements:
    Alert: one message with a severity level.
    check_budgets: compare a month's spending to every budget (80 % warning, 100 % exceeded).
    check_goals: report reached milestones (25/50/75/100 %) and overdue goals.
    collect_alerts: both checks combined, most severe first.

Course concepts illustrated:
    - Decision structures: ``if / elif / else`` chains that classify usage levels.
    - Loops: iterating over budgets and goals.
    - Functions: pure functions with no side effects, easy to test.
    - Tuples and dictionaries: thresholds and severity ordering.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from finance_tracker.tracker import FinanceTracker

WARNING_THRESHOLD = 0.80
EXCEEDED_THRESHOLD = 1.00
GOAL_MILESTONES: tuple[float, ...] = (0.25, 0.50, 0.75, 1.00)

LEVEL_EXCEEDED = "EXCEEDED"
LEVEL_WARNING = "WARNING"
LEVEL_OK = "OK"
LEVEL_INFO = "INFO"
# Lower number = shown first, so the most urgent alerts are at the top.
SEVERITY_ORDER: dict[str, int] = {LEVEL_EXCEEDED: 0, LEVEL_WARNING: 1, LEVEL_INFO: 2, LEVEL_OK: 3}


@dataclass(frozen=True)
class Alert:
    """A single alert shown to the user.

    Attributes:
        level: One of ``EXCEEDED``, ``WARNING``, ``INFO``, ``OK``.
        subject: Budget category or goal name the alert is about.
        message: Human readable explanation.
        ratio: Usage or progress ratio (e.g. 0.85 = 85 %).
    """

    level: str
    subject: str
    message: str
    ratio: float = 0.0

    def __str__(self) -> str:
        """Format the alert for console output.

        Returns:
            The message prefixed by its level, e.g. ``"[WARNING] Groceries ..."``.
        """
        return f"[{self.level}] {self.message}"


def budget_level(ratio: float) -> str:
    """Classify a budget usage ratio.

    Args:
        ratio: Amount spent divided by the budget limit.

    Returns:
        ``EXCEEDED`` (>= 100 %), ``WARNING`` (>= 80 %) or ``OK``.

    Example:
        >>> budget_level(0.85)
        'WARNING'
    """
    # Concept: decision structure — thresholds are tested from most to least severe
    if ratio >= EXCEEDED_THRESHOLD:
        return LEVEL_EXCEEDED
    elif ratio >= WARNING_THRESHOLD:
        return LEVEL_WARNING
    else:
        return LEVEL_OK


def check_budgets(
    tracker: FinanceTracker, month: str | None = None, include_ok: bool = False
) -> list[Alert]:
    """Compare spending in a month against each category budget.

    Args:
        tracker: The tracker holding budgets and transactions.
        month: ``YYYY-MM`` to check; defaults to the latest month with data.
        include_ok: Also return budgets below the warning threshold.

    Returns:
        Alerts sorted from most to least severe.
    """
    month = month or tracker.latest_month()
    if month is None:
        return []
    spent_by_category = tracker.spending_by_category(month)
    alerts: list[Alert] = []
    # Concept: loop + decision — build one alert per budget that needs attention
    for category, budget in sorted(tracker.budgets.items()):
        spent = spent_by_category.get(category, 0.0)
        ratio = budget.usage(spent)
        level = budget_level(ratio)
        if level == LEVEL_OK and not include_ok:
            continue
        if spent == budget.monthly_limit:
            detail = "limit reached"
        elif level == LEVEL_EXCEEDED:
            detail = f"over by ${spent - budget.monthly_limit:,.2f}"
        else:
            detail = f"${budget.monthly_limit - spent:,.2f} left"
        alerts.append(
            Alert(
                level=level,
                subject=category,
                message=(
                    f"{category} ({month}): ${spent:,.2f} of ${budget.monthly_limit:,.2f} "
                    f"({ratio:.0%}) — {detail}"
                ),
                ratio=ratio,
            )
        )
    return sorted(alerts, key=lambda a: (SEVERITY_ORDER[a.level], -a.ratio))


def reached_milestone(progress: float) -> float | None:
    """Return the highest milestone reached for a progress ratio.

    Args:
        progress: Saved amount divided by the target (0.0 to 1.0).

    Returns:
        One of ``GOAL_MILESTONES`` (e.g. 0.5), or None below the first milestone.

    Example:
        >>> reached_milestone(0.6)
        0.5
    """
    reached = [m for m in GOAL_MILESTONES if progress >= m]
    return reached[-1] if reached else None


def check_goals(tracker: FinanceTracker, today: date | None = None) -> list[Alert]:
    """Report savings-goal milestones and overdue goals.

    Args:
        tracker: The tracker holding goals.
        today: Reference date for deadlines (defaults to today).

    Returns:
        One alert per goal that has reached a milestone or is overdue.
    """
    today = today or date.today()
    alerts: list[Alert] = []
    for goal in tracker.goals.values():
        milestone = reached_milestone(goal.progress)
        if goal.is_complete:
            alerts.append(
                Alert(LEVEL_OK, goal.name, f"Goal '{goal.name}' reached! 🎉", goal.progress)
            )
        elif goal.deadline and goal.deadline < today:
            alerts.append(
                Alert(
                    LEVEL_WARNING,
                    goal.name,
                    f"Goal '{goal.name}' missed its deadline {goal.deadline} "
                    f"(${goal.remaining:,.2f} still needed)",
                    goal.progress,
                )
            )
        elif milestone is not None:
            alerts.append(
                Alert(
                    LEVEL_INFO,
                    goal.name,
                    f"Goal '{goal.name}' passed the {milestone:.0%} milestone "
                    f"(${goal.saved:,.2f} of ${goal.target:,.2f})",
                    goal.progress,
                )
            )
    return sorted(alerts, key=lambda a: (SEVERITY_ORDER[a.level], a.subject))


def collect_alerts(
    tracker: FinanceTracker, month: str | None = None, today: date | None = None
) -> list[Alert]:
    """Budget alerts followed by goal alerts, each group sorted by severity.

    Args:
        tracker: The tracker holding budgets, goals and transactions.
        month: ``YYYY-MM`` for the budget check (default: latest month with data).
        today: Reference date for goal deadlines (default: today).

    Returns:
        All alerts, most severe first within each group.
    """
    return check_budgets(tracker, month) + check_goals(tracker, today)
