"""Persistence layer: save and load data as JSON and CSV files.

Main elements:
    AppState: container for everything loaded from disk (plus any warnings).
    save_json / load_json: full state (transactions, budgets, goals) in one JSON file.
    save_csv / load_csv: transactions only, as a flat table readable by Excel and pandas.

Design notes:
    - Writes are atomic: data goes to a temporary file that then replaces the target,
      so a crash mid-save never leaves a half-written file.
    - A corrupted JSON file is kept as a timestamped backup and the app starts with an
      empty state instead of crashing.
    - Invalid rows are skipped and reported as warnings rather than aborting the load.

Course concepts illustrated:
    - File handling: ``pathlib``, ``open`` with context managers, ``json`` and ``csv``.
    - Exceptions: ``try / except / else`` (load_json) and ``try / except / finally``
      (_atomic_write), re-raising low-level errors as ``StorageError``.
    - Lists and dictionaries: building the serialized structures.
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from finance_tracker.exceptions import StorageError, ValidationError
from finance_tracker.models import Budget, SavingsGoal, Transaction

CSV_FIELDS: list[str] = ["id", "date", "amount", "kind", "category", "description"]
SCHEMA_VERSION = 1
ENCODING = "utf-8"
# "utf-8-sig" also accepts the invisible BOM that Excel adds to "CSV UTF-8" files.
CSV_READ_ENCODING = "utf-8-sig"
SECTIONS: tuple[str, ...] = ("transactions", "budgets", "goals")


@dataclass
class AppState:
    """Everything that can be loaded from disk.

    Attributes:
        transactions: Loaded transactions.
        budgets: Budgets keyed by category.
        goals: Savings goals keyed by name.
        warnings: Human readable messages about skipped rows or recovered files.
    """

    transactions: list[Transaction] = field(default_factory=list)
    budgets: dict[str, Budget] = field(default_factory=dict)
    goals: dict[str, SavingsGoal] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _atomic_write(path: Path, write_func: Any, newline: str | None = None) -> None:
    """Write a file atomically via a temporary file in the same directory.

    Args:
        path: Destination file.
        write_func: Callable receiving the open text file object.
        newline: Passed to ``open``; ``""`` is required for the csv module.

    Raises:
        StorageError: If the directory cannot be created or the file cannot be written.
    """
    path = Path(path)
    tmp_name: str | None = None
    # Concept: exception handling — try/except/finally guarantees cleanup of the temp file
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding=ENCODING, newline=newline) as handle:
            write_func(handle)
        # replace() is atomic on the same filesystem: readers see the old or new file,
        # never a partial one.
        Path(tmp_name).replace(path)
        tmp_name = None
    except OSError as exc:
        raise StorageError(f"Could not write '{path}': {exc.strerror or exc}") from exc
    finally:
        if tmp_name is not None:
            Path(tmp_name).unlink(missing_ok=True)


def _backup_corrupted(path: Path) -> Path:
    """Rename a corrupted file so that it is preserved but no longer loaded.

    Args:
        path: The unreadable file.

    Returns:
        The path of the backup copy.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.corrupted-{stamp}")
    path.replace(backup)
    return backup


def save_json(
    path: Path | str,
    transactions: list[Transaction],
    budgets: dict[str, Budget] | None = None,
    goals: dict[str, SavingsGoal] | None = None,
) -> Path:
    """Save the complete application state to a JSON file.

    Args:
        path: Destination ``.json`` file (parent folders are created).
        transactions: Transactions to save.
        budgets: Budgets keyed by category.
        goals: Savings goals keyed by name.

    Returns:
        The path written.

    Raises:
        StorageError: If the file cannot be written.
    """
    path = Path(path)
    # Concept: dictionary + list comprehension — build a JSON-ready nested structure
    payload: dict[str, Any] = {
        "version": SCHEMA_VERSION,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "transactions": [t.to_dict() for t in transactions],
        "budgets": [b.to_dict() for b in (budgets or {}).values()],
        "goals": [g.to_dict() for g in (goals or {}).values()],
    }
    _atomic_write(path, lambda handle: json.dump(payload, handle, indent=2))
    return path


def load_json(path: Path | str, recover: bool = True) -> AppState:
    """Load the complete application state from a JSON file.

    A missing file is not an error (first run): an empty state is returned.

    Args:
        path: The ``.json`` file to read.
        recover: When True, a corrupted file is backed up and an empty state is
            returned; when False, a ``StorageError`` is raised instead.

    Returns:
        The loaded ``AppState``. Invalid records are skipped and listed in ``warnings``.

    Raises:
        StorageError: If the file cannot be read, or is corrupted and ``recover`` is False.
    """
    path = Path(path)
    state = AppState()
    if not path.exists():
        state.warnings.append(f"No data file at '{path}' — starting with empty data.")
        return state

    # Concept: exception handling — recover from a corrupted JSON file
    try:
        # Concept: file handling — `with` closes the file even if json.load fails
        with path.open("r", encoding=ENCODING) as handle:
            payload = json.load(handle)
        _check_structure(payload)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        if not recover:
            raise StorageError(f"Corrupted JSON file '{path}': {exc}") from exc
        backup = _backup_corrupted(path)
        state.warnings.append(
            f"'{path.name}' was corrupted ({exc}); a backup was saved as '{backup.name}'."
        )
    except OSError as exc:
        raise StorageError(f"Could not read '{path}': {exc.strerror or exc}") from exc
    else:
        # `else` runs only when the file was read and parsed without error.
        _fill_state(state, payload)
    return state


def _check_structure(payload: Any) -> None:
    """Make sure a parsed JSON document has the shape this app writes.

    Valid JSON can still be unusable, e.g. ``{"transactions": null}``; treating it
    like a syntax error lets the normal corrupted-file recovery handle it.

    Args:
        payload: The value returned by ``json.load``.

    Raises:
        ValueError: If the top level is not an object or a section is not a list.
    """
    if not isinstance(payload, dict):
        raise ValueError("top-level JSON value must be an object")
    for section in SECTIONS:
        if not isinstance(payload.get(section, []), list):
            raise ValueError(f"'{section}' must be a list")


def _fill_state(state: AppState, payload: dict[str, Any]) -> None:
    """Convert the JSON sections into model objects, skipping invalid records.

    Args:
        state: The state to fill (modified in place).
        payload: A JSON document already checked by ``_check_structure``.
    """
    # Concept: set — remembers ids already loaded so duplicates are detected in O(1)
    seen_ids: set[str] = set()
    # Concept: loop + exception handling — one bad record must not lose all the others
    for index, raw in enumerate(payload.get("transactions", []), start=1):
        try:
            transaction = Transaction.from_dict(raw)
        except (ValidationError, TypeError, AttributeError) as exc:
            state.warnings.append(f"Skipped transaction #{index}: {exc}")
            continue
        if transaction.id in seen_ids:
            state.warnings.append(f"Skipped transaction #{index}: duplicate id '{transaction.id}'")
            continue
        seen_ids.add(transaction.id)
        state.transactions.append(transaction)
    for raw in payload.get("budgets", []):
        try:
            budget = Budget.from_dict(raw)
            state.budgets[budget.category] = budget
        except (ValidationError, TypeError, AttributeError) as exc:
            state.warnings.append(f"Skipped budget: {exc}")
    for raw in payload.get("goals", []):
        try:
            goal = SavingsGoal.from_dict(raw)
            state.goals[goal.name] = goal
        except (ValidationError, TypeError, AttributeError) as exc:
            state.warnings.append(f"Skipped goal: {exc}")


def save_csv(path: Path | str, transactions: list[Transaction]) -> Path:
    """Export transactions to a CSV file (one row per transaction).

    Args:
        path: Destination ``.csv`` file (parent folders are created).
        transactions: Transactions to export.

    Returns:
        The path written.

    Raises:
        StorageError: If the file cannot be written.
    """
    path = Path(path)

    def write_rows(handle: Any) -> None:
        """Write the header and one row per transaction to an open file."""
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for transaction in transactions:
            writer.writerow(transaction.to_dict())

    _atomic_write(path, write_rows, newline="")
    return path


def load_csv(path: Path | str) -> AppState:
    """Import transactions from a CSV file.

    Args:
        path: The ``.csv`` file to read. Required columns: date, amount, kind, category.

    Returns:
        An ``AppState`` whose ``transactions`` are filled; invalid rows are skipped
        and reported in ``warnings``.

    Raises:
        StorageError: If the file does not exist, cannot be read, or lacks the
            required columns.
    """
    path = Path(path)
    state = AppState()
    required = {"date", "amount", "kind", "category"}
    try:
        with path.open("r", encoding=CSV_READ_ENCODING, newline="") as handle:
            reader = csv.DictReader(handle)
            # Concept: set — set difference finds the missing columns in one expression
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise StorageError(
                    f"CSV file '{path.name}' is missing columns: {', '.join(sorted(missing))}"
                )
            # start=2 because line 1 is the header — matches what users see in Excel
            seen_ids: set[str] = set()
            for line_number, row in enumerate(reader, start=2):
                try:
                    transaction = Transaction.from_dict(row)
                except ValidationError as exc:
                    state.warnings.append(f"Skipped CSV line {line_number}: {exc}")
                    continue
                if transaction.id in seen_ids:
                    state.warnings.append(
                        f"Skipped CSV line {line_number}: duplicate id '{transaction.id}'"
                    )
                    continue
                seen_ids.add(transaction.id)
                state.transactions.append(transaction)
    except StorageError:
        # StorageError is an OSError subclass: let it pass through unchanged
        # instead of being re-wrapped by the generic handler below.
        raise
    except FileNotFoundError as exc:
        raise StorageError(f"CSV file not found: '{path}'") from exc
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise StorageError(f"Could not read CSV '{path}': {exc}") from exc
    return state
