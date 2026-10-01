def parse_amount(value: float | int | str) -> float:
    if isinstance(value, bool):  # bool is a subclass of int — reject it explicitly
        raise InvalidTransactionError("Amount must be a number")
    try:
        # Users often type currency symbols and thousands separators; accept them.
        cleaned = str(value).replace("$", "").replace(",", "").strip()
        amount = float(cleaned)
    except ValueError as exc:
        raise InvalidTransactionError(f"Invalid amount '{value}': not a number") from exc
    if not math.isfinite(amount):  # rejects NaN and infinity
        raise InvalidTransactionError("Amount must be a finite number")
    # Round first: "0.004" would otherwise pass the check and be stored as 0.00.
    amount = round(amount, 2)
    if amount <= 0:
        raise InvalidTransactionError("Amount must be at least 0.01")
    if amount > MAX_AMOUNT:
        raise InvalidTransactionError(f"Amount must not exceed {MAX_AMOUNT:,.0f}")
    return amount
