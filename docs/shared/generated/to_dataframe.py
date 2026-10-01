def to_dataframe(transactions: Iterable[Transaction]) -> pd.DataFrame:
    # Concept: pandas — create a DataFrame from a list of dictionaries
    df = pd.DataFrame([t.to_dict() for t in transactions], columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float)
    # Vectorised: one expression for the whole column instead of a Python loop.
    df["signed_amount"] = df["amount"].where(df["kind"] == INCOME, -df["amount"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    return df.sort_values("date", ignore_index=True)
