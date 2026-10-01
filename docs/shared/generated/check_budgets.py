def check_budgets(
    tracker: FinanceTracker, month: str | None = None, include_ok: bool = False
) -> list[Alert]:
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
