def category_breakdown(df: pd.DataFrame, kind: str = EXPENSE) -> pd.DataFrame:
    subset = df[df["kind"] == kind]
    if subset.empty:
        return pd.DataFrame(columns=["category", "total", "share", "count"])
    # Concept: pandas — groupby + named aggregation computes several stats at once
    grouped = (
        subset.groupby("category")
        .agg(total=("amount", "sum"), count=("amount", "size"))
        .sort_values("total", ascending=False)
        .reset_index()
    )
    grouped["share"] = grouped["total"] / grouped["total"].sum() * 100
    return grouped[["category", "total", "share", "count"]].round(2)
