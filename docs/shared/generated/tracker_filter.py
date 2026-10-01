def filter(
    self,
    kind: str | None = None,
    categories: Iterable[str] | None = None,
    start: date | str | None = None,
    end: date | str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
) -> list[Transaction]:
    wanted = {normalize_category(c) for c in categories} if categories else None
    kind = kind.strip().lower() if kind else None
    start_date = parse_date(start) if start else None
    end_date = parse_date(end) if end else None
    results: list[Transaction] = []
    # Concept: loop + decision — each `continue` skips a transaction failing one test
    for t in self.transactions:
        if kind and t.kind != kind:
            continue
        if wanted is not None and t.category not in wanted:
            continue
        if start_date and t.date < start_date:
            continue
        if end_date and t.date > end_date:
            continue
        if min_amount is not None and t.amount < min_amount:
            continue
        if max_amount is not None and t.amount > max_amount:
            continue
        results.append(t)
    return sorted(results, key=lambda t: t.date)
