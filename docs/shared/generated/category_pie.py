def category_pie(df: pd.DataFrame, title: str = "Expenses by Category", dpi: float = DPI) -> Figure:
    breakdown = analytics.category_breakdown(df)
    if breakdown.empty:
        return _empty_figure(title, dpi=dpi)
    totals = breakdown.set_index("category")["total"]
    if len(totals) > MAX_PIE_SLICES:
        head = totals.iloc[: MAX_PIE_SLICES - 1]
        rest = pd.Series({"All others": totals.iloc[MAX_PIE_SLICES - 1 :].sum()})
        totals = pd.concat([head, rest])

    fig = Figure(figsize=FIGSIZE, dpi=dpi)
    ax = fig.add_subplot()
    wedges, _texts, _autotexts = ax.pie(
        totals.values,
        autopct="%1.0f%%",
        startangle=90,
        counterclock=False,
        pctdistance=0.78,
        colors=PALETTE[: len(totals)],
        wedgeprops={"width": 0.45, "edgecolor": "white"},  # donut: easier to compare
        textprops={"color": "white", "fontsize": 9, "weight": "bold"},
    )
    ax.legend(
        wedges,
        [f"{escape_dollars(name)}  ${value:,.0f}" for name, value in totals.items()],
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        frameon=False,
    )
    ax.text(0, 0, f"${totals.sum():,.0f}\ntotal", ha="center", va="center", fontsize=12)
    ax.set_title(title, weight="bold")
    ax.axis("equal")
    fig.tight_layout()
    return fig
