def __init__(self, transactions: Iterable[Transaction] | None = None) -> None:
    # Concept: list — transactions are ordered and may contain look-alike entries
    self.transactions: list[Transaction] = []
    # Concept: dictionary — O(1) lookup of a budget/goal by its name
    self.budgets: dict[str, Budget] = {}
    self.goals: dict[str, SavingsGoal] = {}
    # Concept: set — guarantees unique category names
    self.categories: set[str] = set(DEFAULT_EXPENSE_CATEGORIES | DEFAULT_INCOME_CATEGORIES)
    for transaction in transactions or []:
        self._store(transaction)
