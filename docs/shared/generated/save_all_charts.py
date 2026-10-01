def save_all_charts(
    df: pd.DataFrame, goals: Iterable[SavingsGoal], out_dir: Path = CHARTS_DIR
) -> list[Path]:
    # Concept: dictionary — map each output file name to the function that draws it
    charts = {
        "category_pie.png": category_pie(df),
        "monthly_income_expenses.png": monthly_bars(df),
        "spending_trend.png": trend_line(df),
        "goals_progress.png": goals_progress(goals),
    }
    return [save_figure(fig, Path(out_dir) / name) for name, fig in charts.items()]
