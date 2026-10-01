class FinanceTrackerError(Exception):
    """Base class for every error raised by the finance tracker."""


class ValidationError(FinanceTrackerError, ValueError):
    """Raised when user-supplied data is invalid.

    Inherits from ``ValueError`` as well, so generic code that expects a
    ``ValueError`` for bad input keeps working.
    """


class InvalidTransactionError(ValidationError):
    """Raised when a transaction has an invalid amount, date, kind or category."""


class InvalidBudgetError(ValidationError):
    """Raised when a budget limit or category is invalid."""


class InvalidGoalError(ValidationError):
    """Raised when a savings goal has an invalid name, target or deadline."""


class TransactionNotFoundError(FinanceTrackerError, KeyError):
    """Raised when no transaction matches the requested id."""

    def __str__(self) -> str:
        """Return the plain message.

        KeyError wraps its message in quotes; a plain message is friendlier in the UI.

        Returns:
            The error message without surrounding quotes.
        """
        return str(self.args[0]) if self.args else "Transaction not found"


class StorageError(FinanceTrackerError, OSError):
    """Raised when data cannot be saved to or loaded from disk."""
