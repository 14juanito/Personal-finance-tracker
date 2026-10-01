def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon="💰", layout="wide")
    st.title("💰 Personal Finance Dashboard")
    loaded = choose_data()
    if loaded is None:
        return
    tracker, label = loaded
    df_all = analytics.to_dataframe(tracker.transactions)
    if df_all.empty:
        st.warning("This file contains no transactions.")
        return
    start, end, categories, kind = sidebar_filters(df_all)
    # Concept: pandas — the sidebar filters become boolean masks on the DataFrame
    df = analytics.filter_dataframe(df_all, start, end, categories)
    if kind == "Expenses":
        df = df[df["kind"] == EXPENSE]
    elif kind == "Income":
        df = df[df["kind"] == INCOME]
    st.caption(f"{label} · {start} → {end} · {len(df)} of {len(df_all)} transactions")
    if df.empty:
        st.warning("No transactions match the filters.")
        return
    kpi_row(df)
    tabs = st.tabs(["Overview", "Trends", "Budgets & Alerts", "Savings Goals", "Transactions"])
    with tabs[0]:
        overview_tab(df)
    with tabs[1]:
        trends_tab(df)
    with tabs[2]:
        budgets_tab(tracker)
    with tabs[3]:
        goals_tab(tracker)
    with tabs[4]:
        transactions_tab(df)
