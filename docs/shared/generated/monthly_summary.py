def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
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
