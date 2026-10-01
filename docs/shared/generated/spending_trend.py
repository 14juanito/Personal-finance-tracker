def spending_trend(df: pd.DataFrame, window: int = DEFAULT_TREND_WINDOW) -> pd.DataFrame:
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
