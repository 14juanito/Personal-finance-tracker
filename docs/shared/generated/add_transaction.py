def add_transaction(
    self,
    date_value: date | str,
    amount: float | str,
    kind: str,
    category: str,
    description: str = "",
) -> Transaction:
    transaction = Transaction(
        date=date_value,
        amount=amount,
        kind=kind,
        category=category,
        description=description,
    )
    return self._store(transaction)
