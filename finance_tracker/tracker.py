"""FinanceTracker: the central object that holds and manipulates all user data.

Main elements:
    FinanceTracker: stores transactions (list), budgets and goals (dicts) and
        categories (set); offers add / update / delete / search / filter, summaries,
        and save / load helpers for JSON and CSV.
    DEFAULT_EXPENSE_CATEGORIES / DEFAULT_INCOME_CATEGORIES: starter category sets.

Course concepts illustrated:
    - OOP: a class that encapsulates state and exposes methods.
    - Lists, dictionaries and sets, each chosen for what it is good at.
    - Loops and decisions: filtering and aggregating transactions.
    - Functions: small focused methods with type hints and docstrings.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

from finance_tracker import storage
from finance_tracker.exceptions import (
    InvalidGoalError,
    InvalidTransactionError,
    TransactionNotFoundError,
)
from finance_tracker.models import (
    EXPENSE,
    INCOME,
    Budget,
    SavingsGoal,
    Transaction,
    normalize_category,
    parse_date,
)

DEFAULT_EXPENSE_CATEGORIES: frozenset[str] = frozenset(
    {
        "Housing",
        "Groceries",
        "Dining Out",
        "Transportation",
        "Utilities",
        "Entertainment",
        "Health",
        "Shopping",
        "Education",
        "Other",
    }
)
DEFAULT_INCOME_CATEGORIES: frozenset[str] = frozenset({"Salary", "Freelance", "Gifts", "Other"})


# Concept: OOP — the class hides its data structures behind well-named methods
class FinanceTracker:
    """In-memory store of transactions, budgets and savings goals.

    Attributes:
        transactions: All transactions, kept in insertion order.
        budgets: Monthly budgets keyed by category name.
        goals: Savings goals keyed by goal name.
        categories: Every category name known to the tracker.

    Example:
        >>> tracker = FinanceTracker()
        >>> _ = tracker.add_transaction("2025-01-03", 2500, "income", "Salary")
        >>> _ = tracker.add_transaction("2025-01-04", 60, "expense", "Groceries")
        >>> tracker.balance()
        2440.0
    """

    def __init__(self, transactions: Iterable[Transaction] | None = None) -> None:
        """Create a tracker, optionally pre-filled with transactions.

        Args:
            transactions: Initial transactions.
        """
        # Concept: list — transactions are ordered and may contain look-alike entries
        self.transactions: list[Transaction] = []
        # Concept: dictionary — O(1) lookup of a budget/goal by its name
        self.budgets: dict[str, Budget] = {}
        self.goals: dict[str, SavingsGoal] = {}
        # Concept: set — guarantees unique category names
        self.categories: set[str] = set(DEFAULT_EXPENSE_CATEGORIES | DEFAULT_INCOME_CATEGORIES)
        for transaction in transactions or []:
            self._store(transaction)

    # ------------------------------------------------------------------ transactions
    def _store(self, transaction: Transaction) -> Transaction:
        """Append a transaction and register its category."""
        self.transactions.append(transaction)
        self.categories.add(transaction.category)
        return transaction

    def add_transaction(
        self,
        date_value: date | str,
        amount: float | str,
        kind: str,
        category: str,
        description: str = "",
    ) -> Transaction:
        """Create, validate and store a new transaction.

        Args:
            date_value: Transaction date (``date`` or ``YYYY-MM-DD``).
            amount: Positive amount.
            kind: ``"income"`` or ``"expense"``.
            category: Category name (new names are added to ``categories``).
            description: Optional note.

        Returns:
            The stored transaction.

        Raises:
            InvalidTransactionError: If any value is invalid.
        """
        transaction = Transaction(
            date=date_value,
            amount=amount,
            kind=kind,
            category=category,
            description=description,
        )
        return self._store(transaction)

    def get_transaction(self, transaction_id: str) -> Transaction:
        """Return the transaction with the given id.

        Raises:
            TransactionNotFoundError: If no transaction has this id.
        """
        # Concept: loop + decision — linear search is fine for a personal-size dataset
        for transaction in self.transactions:
            if transaction.id == transaction_id:
                return transaction
        raise TransactionNotFoundError(f"No transaction with id '{transaction_id}'")

    def update_transaction(self, transaction_id: str, **changes: Any) -> Transaction:
        """Modify fields of an existing transaction.

        The updated transaction is fully re-validated; if validation fails the
        original is left untouched.

        Args:
            transaction_id: Id of the transaction to modify.
            **changes: Any of ``date``, ``amount``, ``kind``, ``category``, ``description``.

        Returns:
            The updated transaction.

        Raises:
            TransactionNotFoundError: If the id is unknown.
            InvalidTransactionError: If a field name or value is invalid.
        """
        allowed = {"date", "amount", "kind", "category", "description"}
        unknown = set(changes) - allowed
        if unknown:
            raise InvalidTransactionError(f"Cannot update field(s): {', '.join(sorted(unknown))}")
        current = self.get_transaction(transaction_id)
        # Building a new object validates everything before we replace the old one.
        data = current.to_dict() | {key: value for key, value in changes.items()}
        updated = Transaction.from_dict(data)
        index = self.transactions.index(current)
        self.transactions[index] = updated
        self.categories.add(updated.category)
        return updated

    def delete_transaction(self, transaction_id: str) -> Transaction:
        """Remove a transaction.

        Returns:
            The removed transaction.

        Raises:
            TransactionNotFoundError: If the id is unknown.
        """
        transaction = self.get_transaction(transaction_id)
        self.transactions.remove(transaction)
        return transaction

    def search(self, text: str) -> list[Transaction]:
        """Case-insensitive search in descriptions and category names.

        Args:
            text: Substring to look for.

        Returns:
            Matching transactions (empty list if ``text`` is blank).
        """
        needle = text.strip().lower()
        if not needle:
            return []
        return [
            t
            for t in self.transactions
            if needle in t.description.lower() or needle in t.category.lower()
        ]

    def filter(
        self,
        kind: str | None = None,
        categories: Iterable[str] | None = None,
        start: date | str | None = None,
        end: date | str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
    ) -> list[Transaction]:
        """Return transactions matching every given criterion.

        Args:
            kind: ``"income"`` or ``"expense"``.
            categories: Allowed categories.
            start: First date included.
            end: Last date included.
            min_amount: Minimum amount included.
            max_amount: Maximum amount included.

        Returns:
            Matching transactions sorted by date.
        """
        wanted = {normalize_category(c) for c in categories} if categories else None
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

    def sorted_transactions(self, newest_first: bool = True) -> list[Transaction]:
        """Return all transactions sorted by date."""
        return sorted(self.transactions, key=lambda t: t.date, reverse=newest_first)

    # ------------------------------------------------------------------ summaries
    def total(self, kind: str, month: str | None = None) -> float:
        """Sum of income or expenses, optionally for one month.

        Args:
            kind: ``"income"`` or ``"expense"``.
            month: ``YYYY-MM`` to restrict the sum, or None for all time.

        Returns:
            The total rounded to cents.
        """
        return round(
            sum(
                t.amount
                for t in self.transactions
                if t.kind == kind and (month is None or t.month == month)
            ),
            2,
        )

    def balance(self, month: str | None = None) -> float:
        """Income minus expenses (all time, or for one ``YYYY-MM`` month)."""
        return round(self.total(INCOME, month) - self.total(EXPENSE, month), 2)

    def spending_by_category(self, month: str | None = None) -> dict[str, float]:
        """Total expenses per category, largest first.

        Args:
            month: ``YYYY-MM`` to restrict the totals, or None for all time.

        Returns:
            Mapping category → amount spent.
        """
        totals: dict[str, float] = {}
        for t in self.transactions:
            if t.is_expense and (month is None or t.month == month):
                # dict.get with a default avoids a separate "is the key there?" check
                totals[t.category] = totals.get(t.category, 0.0) + t.amount
        return {
            category: round(amount, 2)
            for category, amount in sorted(totals.items(), key=lambda item: -item[1])
        }

    def months(self) -> list[str]:
        """Sorted list of distinct ``YYYY-MM`` months that have transactions."""
        return sorted({t.month for t in self.transactions})

    def latest_month(self) -> str | None:
        """Most recent month with data, or None when the tracker is empty."""
        months = self.months()
        return months[-1] if months else None

    def expense_categories(self) -> list[str]:
        """Sorted expense categories: defaults plus any category used by an expense."""
        used = {t.category for t in self.transactions if t.is_expense}
        return sorted(DEFAULT_EXPENSE_CATEGORIES | used)

    def income_categories(self) -> list[str]:
        """Sorted income categories: defaults plus any category used by an income."""
        used = {t.category for t in self.transactions if t.kind == INCOME}
        return sorted(DEFAULT_INCOME_CATEGORIES | used)

    # ------------------------------------------------------------------ budgets & goals
    def set_budget(self, category: str, monthly_limit: float | str) -> Budget:
        """Create or replace the monthly budget for a category.

        Raises:
            InvalidBudgetError: If the category or limit is invalid.
        """
        budget = Budget(category=category, monthly_limit=monthly_limit)
        self.budgets[budget.category] = budget
        self.categories.add(budget.category)
        return budget

    def remove_budget(self, category: str) -> bool:
        """Delete a budget. Returns True if one existed."""
        return self.budgets.pop(normalize_category(category), None) is not None

    def add_goal(
        self,
        name: str,
        target: float | str,
        saved: float | str = 0.0,
        deadline: date | str | None = None,
    ) -> SavingsGoal:
        """Create a new savings goal.

        Raises:
            InvalidGoalError: If the name already exists or a value is invalid.
        """
        goal = SavingsGoal(name=name, target=target, saved=saved, deadline=deadline)
        if goal.name in self.goals:
            raise InvalidGoalError(f"A goal named '{goal.name}' already exists")
        self.goals[goal.name] = goal
        return goal

    def contribute_to_goal(self, name: str, amount: float | str) -> SavingsGoal:
        """Add money to an existing goal.

        Raises:
            InvalidGoalError: If the goal does not exist or the amount is invalid.
        """
        goal = self.goals.get(" ".join(name.split()))
        if goal is None:
            raise InvalidGoalError(f"No goal named '{name}'")
        goal.contribute(amount)
        return goal

    def remove_goal(self, name: str) -> bool:
        """Delete a goal. Returns True if one existed."""
        return self.goals.pop(" ".join(name.split()), None) is not None

    # ------------------------------------------------------------------ persistence
    def save_json(self, path: Path | str) -> Path:
        """Save transactions, budgets and goals to a JSON file."""
        return storage.save_json(path, self.transactions, self.budgets, self.goals)

    def export_csv(self, path: Path | str) -> Path:
        """Export transactions to a CSV file."""
        return storage.save_csv(path, self.sorted_transactions(newest_first=False))

    def import_csv(self, path: Path | str) -> list[str]:
        """Append transactions from a CSV file, skipping ids already present.

        Returns:
            Warnings about skipped rows or duplicates.
        """
        state = storage.load_csv(path)
        known_ids = {t.id for t in self.transactions}
        duplicates = 0
        for transaction in state.transactions:
            if transaction.id in known_ids:
                duplicates += 1
                continue
            self._store(transaction)
            known_ids.add(transaction.id)
        if duplicates:
            state.warnings.append(f"Ignored {duplicates} transaction(s) already present.")
        return state.warnings

    @classmethod
    def load_json(cls, path: Path | str) -> tuple[FinanceTracker, list[str]]:
        """Create a tracker from a JSON file.

        Returns:
            A tuple ``(tracker, warnings)``; a missing or corrupted file yields an
            empty tracker and a warning instead of an exception.
        """
        state = storage.load_json(path)
        tracker = cls(state.transactions)
        tracker.budgets = state.budgets
        tracker.goals = state.goals
        tracker.categories.update(state.budgets)
        return tracker, state.warnings

    @classmethod
    def from_csv(cls, path: Path | str) -> tuple[FinanceTracker, list[str]]:
        """Create a tracker from a CSV file of transactions.

        Raises:
            StorageError: If the file is missing or unreadable.
        """
        state = storage.load_csv(path)
        return cls(state.transactions), state.warnings
