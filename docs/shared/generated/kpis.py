def kpis(df: pd.DataFrame) -> dict[str, float]:
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
