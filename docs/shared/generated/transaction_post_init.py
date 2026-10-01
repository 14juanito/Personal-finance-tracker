def __post_init__(self) -> None:
    self.date = parse_date(self.date)
    self.amount = parse_amount(self.amount)
    self.kind = str(self.kind).strip().lower()
    # Concept: decision structure — reject anything outside the allowed kinds
    if self.kind not in VALID_KINDS:
        raise InvalidTransactionError(
            f"Invalid kind '{self.kind}': expected one of {sorted(VALID_KINDS)}"
        )
    self.category = normalize_category(self.category)
    if not self.category:
        raise InvalidTransactionError("Category must not be empty")
    self.description = str(self.description or "").strip()
    if len(self.description) > MAX_DESCRIPTION_LENGTH:
        raise InvalidTransactionError(
            f"Description must be at most {MAX_DESCRIPTION_LENGTH} characters"
        )
    if not self.id:
        self.id = _new_id()
