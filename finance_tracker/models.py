"""Domain models: transactions, savings goals and budgets.

Main elements:
    Transaction: one income or expense entry (validated on creation).
    SavingsGoal: a named target amount with progress tracking.
    Budget: a monthly spending limit for one expense category.
    parse_date / parse_amount: shared helpers that turn raw user text into typed values.

Course concepts illustrated:
    - OOP: dataclasses with methods, properties and class methods.
    - Exceptions: validation in ``__post_init__`` raises custom exceptions.
    - Dictionaries: ``to_dict`` / ``from_dict`` for serialization.
    - Sets: allowed transaction kinds.
"""

from __future__ import annotations

import math
import string
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from finance_tracker.exceptions import (
    InvalidBudgetError,
    InvalidGoalError,
    InvalidTransactionError,
)

INCOME = "income"
EXPENSE = "expense"
# Concept: set — membership tests on a fixed collection of allowed values are O(1)
VALID_KINDS: frozenset[str] = frozenset({INCOME, EXPENSE})
DATE_FORMAT = "%Y-%m-%d"
MAX_AMOUNT = 1_000_000.0
MAX_DESCRIPTION_LENGTH = 120


def parse_date(value: date | str) -> date:
    """Convert an ISO string (``YYYY-MM-DD``) or a date into a ``date``.

    Args:
        value: A ``date``/``datetime`` object or an ISO formatted string.

    Returns:
        The corresponding ``date`` object.

    Raises:
        InvalidTransactionError: If the string is not a valid ISO date.

    Example:
        >>> parse_date("2025-03-14")
        datetime.date(2025, 3, 14)
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # Concept: exception handling — translate a low-level ValueError into a domain error
    try:
        return datetime.strptime(str(value).strip(), DATE_FORMAT).date()
    except ValueError as exc:
        raise InvalidTransactionError(f"Invalid date '{value}': expected YYYY-MM-DD") from exc


# Concept: functions — one reusable validator shared by transactions, goals and budgets
def parse_amount(value: float | int | str) -> float:
    """Convert user input into a positive amount rounded to cents.

    Args:
        value: A number or a string such as ``"12.50"`` or ``"$1,200"``.

    Returns:
        The amount as a float rounded to 2 decimals.

    Raises:
        InvalidTransactionError: If the value is not a number, not positive,
            or unrealistically large.
    """
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


def normalize_category(name: str | None) -> str:
    """Return a category name in a canonical form (trimmed, each word capitalized).

    Normalizing avoids "food", "Food " and "FOOD" becoming three categories.
    ``string.capwords`` is used instead of ``str.title`` so that "kid's" stays
    "Kid's" (``title`` would give "Kid'S").

    Args:
        name: Raw category name; None is treated as empty.

    Returns:
        The normalized name, e.g. ``"Dining Out"`` (empty string for blank input).
    """
    if name is None:
        return ""
    return string.capwords(str(name).lower())


def _new_id() -> str:
    """Create a short unique identifier.

    Returns:
        8 random hexadecimal characters, e.g. ``"3f9a0c1d"``.
    """
    return uuid.uuid4().hex[:8]


# Concept: OOP — a dataclass bundles data with the behaviour that validates it
@dataclass
class Transaction:
    """A single income or expense entry.

    Attributes:
        date: Day the transaction happened.
        amount: Positive amount; the sign is given by ``kind``.
        kind: ``"income"`` or ``"expense"``.
        category: Category name (normalized to Title Case).
        description: Optional free text.
        id: Unique identifier, generated automatically.

    Raises:
        InvalidTransactionError: If any field is invalid.

    Example:
        >>> t = Transaction(date="2025-01-05", amount="42.10", kind="expense",
        ...                 category="groceries")
        >>> t.category, t.signed_amount
        ('Groceries', -42.1)
    """

    date: date
    amount: float
    kind: str
    category: str
    description: str = ""
    id: str = field(default_factory=_new_id)

    def __post_init__(self) -> None:
        """Validate and normalize every field right after construction."""
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

    @property
    def is_expense(self) -> bool:
        """bool: True when the transaction is an expense."""
        return self.kind == EXPENSE

    @property
    def signed_amount(self) -> float:
        """float: Amount with a negative sign for expenses (useful for balances)."""
        return -self.amount if self.is_expense else self.amount

    @property
    def month(self) -> str:
        """str: Month of the transaction as ``YYYY-MM``."""
        return self.date.strftime("%Y-%m")

    # Concept: dictionary — a plain dict is the bridge between objects and JSON/CSV files
    def to_dict(self) -> dict[str, Any]:
        """Serialize the transaction to a JSON/CSV friendly dictionary.

        Returns:
            A dict with string/float values only.
        """
        return {
            "id": self.id,
            "date": self.date.strftime(DATE_FORMAT),
            "amount": self.amount,
            "kind": self.kind,
            "category": self.category,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transaction:
        """Build a transaction from a dictionary (e.g. one JSON object or CSV row).

        Args:
            data: Mapping with at least ``date``, ``amount``, ``kind`` and ``category``.

        Returns:
            A validated ``Transaction``.

        Raises:
            InvalidTransactionError: If a required key is missing or a value is invalid.
        """
        try:
            return cls(
                date=data["date"],
                amount=data["amount"],
                kind=data["kind"],
                category=data["category"],
                description=data.get("description") or "",
                id=str(data.get("id") or "") or _new_id(),
            )
        except KeyError as exc:
            raise InvalidTransactionError(f"Missing field {exc} in transaction data") from exc


@dataclass
class SavingsGoal:
    """A savings target, e.g. "Emergency fund: $3,000 by December".

    Attributes:
        name: Unique goal name.
        target: Amount to reach (> 0).
        saved: Amount saved so far (>= 0).
        deadline: Optional target date.

    Raises:
        InvalidGoalError: If the name is empty or amounts are invalid.
    """

    name: str
    target: float
    saved: float = 0.0
    deadline: date | None = None

    def __post_init__(self) -> None:
        """Validate the goal fields."""
        self.name = " ".join(str(self.name).split())
        if not self.name:
            raise InvalidGoalError("Goal name must not be empty")
        try:
            self.target = parse_amount(self.target)
        except InvalidTransactionError as exc:
            raise InvalidGoalError(f"Invalid target: {exc}") from exc
        if isinstance(self.saved, bool):
            raise InvalidGoalError("Saved amount must be a number")
        try:
            self.saved = round(float(self.saved), 2)
        except (TypeError, ValueError) as exc:
            raise InvalidGoalError(f"Invalid saved amount '{self.saved}'") from exc
        if not math.isfinite(self.saved):
            raise InvalidGoalError("Saved amount must be a finite number")
        if self.saved < 0:
            raise InvalidGoalError("Saved amount cannot be negative")
        if self.deadline is not None and self.deadline != "":
            try:
                self.deadline = parse_date(self.deadline)
            except InvalidTransactionError as exc:
                raise InvalidGoalError(str(exc)) from exc
        else:
            self.deadline = None

    @property
    def progress(self) -> float:
        """float: Fraction of the target reached, capped at 1.0."""
        return min(self.saved / self.target, 1.0)

    @property
    def remaining(self) -> float:
        """float: Amount still needed (never negative)."""
        return round(max(self.target - self.saved, 0.0), 2)

    @property
    def is_complete(self) -> bool:
        """bool: True once the saved amount reaches the target."""
        return self.saved >= self.target

    def contribute(self, amount: float | str) -> float:
        """Add money to the goal.

        Args:
            amount: Positive amount to add.

        Returns:
            The new saved total.

        Raises:
            InvalidGoalError: If the amount is not a positive number.
        """
        try:
            value = parse_amount(amount)
        except InvalidTransactionError as exc:
            raise InvalidGoalError(f"Invalid contribution: {exc}") from exc
        self.saved = round(self.saved + value, 2)
        return self.saved

    def to_dict(self) -> dict[str, Any]:
        """Serialize the goal to a JSON friendly dictionary."""
        return {
            "name": self.name,
            "target": self.target,
            "saved": self.saved,
            "deadline": self.deadline.strftime(DATE_FORMAT) if self.deadline else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SavingsGoal:
        """Build a goal from a dictionary.

        Raises:
            InvalidGoalError: If a required key is missing or a value is invalid.
        """
        try:
            return cls(
                name=data["name"],
                target=data["target"],
                saved=data.get("saved", 0.0),
                deadline=data.get("deadline"),
            )
        except KeyError as exc:
            raise InvalidGoalError(f"Missing field {exc} in goal data") from exc


@dataclass
class Budget:
    """A monthly spending limit for one expense category.

    Attributes:
        category: Expense category the limit applies to.
        monthly_limit: Maximum amount to spend per month (> 0).

    Raises:
        InvalidBudgetError: If the category is empty or the limit is invalid.
    """

    category: str
    monthly_limit: float

    def __post_init__(self) -> None:
        """Validate the budget fields."""
        self.category = normalize_category(self.category)
        if not self.category:
            raise InvalidBudgetError("Budget category must not be empty")
        try:
            self.monthly_limit = parse_amount(self.monthly_limit)
        except InvalidTransactionError as exc:
            raise InvalidBudgetError(f"Invalid limit: {exc}") from exc

    def usage(self, spent: float) -> float:
        """Return the fraction of the budget used.

        Args:
            spent: Amount spent in the category this month.

        Returns:
            ``spent / monthly_limit`` (can exceed 1.0 when over budget).
        """
        return spent / self.monthly_limit

    def to_dict(self) -> dict[str, Any]:
        """Serialize the budget to a JSON friendly dictionary."""
        return {"category": self.category, "monthly_limit": self.monthly_limit}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Budget:
        """Build a budget from a dictionary.

        Raises:
            InvalidBudgetError: If a required key is missing or a value is invalid.
        """
        try:
            return cls(category=data["category"], monthly_limit=data["monthly_limit"])
        except KeyError as exc:
            raise InvalidBudgetError(f"Missing field {exc} in budget data") from exc
