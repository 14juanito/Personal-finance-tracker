"""Tests for cli.py: the menu is driven with scripted answers instead of a keyboard.

Main elements:
    Complete console sessions driven by scripted answers, including invalid input.

Course concepts exercised:
    User input/output, loops and decisions, exceptions.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from finance_tracker import cli
from finance_tracker.tracker import FinanceTracker


class Script:
    """Feeds pre-written answers to ``input`` and records everything printed."""

    def __init__(self, answers: list[str]) -> None:
        self._answers: Iterator[str] = iter(answers)
        self.output: list[str] = []

    def input(self, prompt: str) -> str:
        self.output.append(prompt)
        try:
            return next(self._answers)
        except StopIteration:
            raise EOFError from None  # behaves like Ctrl+D when the script runs out

    def print(self, text: str = "") -> None:
        self.output.append(text)

    @property
    def text(self) -> str:
        return "\n".join(self.output)


def make_app(
    tracker: FinanceTracker, answers: list[str], tmp_path: Path
) -> tuple[cli.ConsoleApp, Script]:
    script = Script(answers)
    app = cli.ConsoleApp(
        tracker,
        data_path=tmp_path / "data.json",
        input_func=script.input,
        output_func=script.print,
        charts_dir=tmp_path / "charts",
    )
    return app, script


def test_add_transaction_with_invalid_inputs_reprompts(
    tracker: FinanceTracker, tmp_path: Path
) -> None:
    answers = [
        "1",  # menu: add
        "7",  # invalid kind choice
        "expense",  # kind by name
        "abc",  # invalid amount
        "-5",  # invalid amount
        "450",  # valid
        "2025-02-30",  # invalid date
        "2025-02-20",
        "Groceries",  # category by name
        "Costco",
        "0",  # save and quit
    ]
    app, script = make_app(tracker, answers, tmp_path)
    app.run()

    assert "Please enter a number between 1 and 2" in script.text
    assert "not a number" in script.text
    assert "at least 0.01" in script.text
    assert "Invalid date" in script.text
    assert "[EXCEEDED] Groceries" in script.text  # immediate budget feedback
    assert (tmp_path / "data.json").exists()
    reloaded, _ = FinanceTracker.load_json(tmp_path / "data.json")
    assert reloaded.search("costco")[0].amount == 450


def test_new_category_and_unknown_menu_option(tracker: FinanceTracker, tmp_path: Path) -> None:
    categories = tracker.income_categories()
    answers = ["99", "1", "income", "75", "", str(len(categories) + 1), "", "Tips", "", "0"]
    app, script = make_app(tracker, answers, tmp_path)
    app.run()
    assert "Unknown option" in script.text
    assert "cannot be empty" in script.text
    assert "Tips" in tracker.categories


def test_list_search_and_filter(tracker: FinanceTracker, tmp_path: Path) -> None:
    answers = [
        "2",
        "3", "Text", "rent",
        "3", "Filters", "expense", "Groceries", "2025-02-31", "2025-02-01", "", "", "",
        "3", "Text", "zzz",
        "0",
    ]  # fmt: skip
    app, script = make_app(tracker, answers, tmp_path)
    app.run()
    assert "Weekly shop" in script.text
    assert "Invalid date '2025-02-31'" in script.text
    assert "2 result(s), net total -$2,400.00" in script.text
    assert "1 result(s), net total -$420.00" in script.text
    assert "No matching transactions." in script.text


def test_list_paginates(tmp_path: Path) -> None:
    tracker = FinanceTracker()
    for day in range(1, 21):
        tracker.add_transaction(f"2025-01-{day:02d}", day, "expense", "Food")
    app, script = make_app(tracker, ["2", "q", "0"], tmp_path)
    app.run()
    assert "15/20 shown" in script.text


def test_edit_and_delete(tracker: FinanceTracker, tmp_path: Path) -> None:
    target = tracker.search("pizza")[0]
    answers = [
        "4", target.id, "amount", "oops",  # invalid edit is rejected
        "4", target.id, "amount", "99.99",
        "5", "nope",  # unknown id
        "5", target.id, "maybe", "y",
        "0",
    ]  # fmt: skip
    app, script = make_app(tracker, answers, tmp_path)
    app.run()
    assert "nothing was changed" in script.text
    assert "Transaction updated" in script.text
    assert "No transaction with id 'nope'" in script.text
    assert "Please answer y or n" in script.text
    assert all(t.id != target.id for t in tracker.transactions)


def test_summary_trends_and_charts(tracker: FinanceTracker, tmp_path: Path) -> None:
    app, script = make_app(tracker, ["6", "2025-01", "7", "10", "0"], tmp_path)
    app.run()
    assert "Net:         $1,569.50" in script.text
    assert "Housing" in script.text
    assert "+13.2%" in script.text  # Feb vs Jan expenses
    assert "Top 5 expenses" in script.text
    assert len(list((tmp_path / "charts").glob("*.png"))) == 4


def test_budgets_and_goals(tracker: FinanceTracker, tmp_path: Path) -> None:
    answers = [
        "8", "Set a budget", "Health", "120",
        "8", "Remove a budget", "Housing",
        "9", "Contribute", "Emergency Fund", "500",
        "9", "Add a goal", "Car", "8000", "2027-01-01",
        "9", "Add a goal", "Car", "10", "",  # duplicate name
        "0",
    ]  # fmt: skip
    app, script = make_app(tracker, answers, tmp_path)
    app.run()
    assert tracker.budgets["Health"].monthly_limit == 120
    assert "Housing" not in tracker.budgets
    assert "Milestone reached: 75%" in script.text
    assert "Car" in tracker.goals
    assert "already exists" in script.text


def test_files_menu(tracker: FinanceTracker, tmp_path: Path) -> None:
    csv_path = tmp_path / "export.csv"
    answers = [
        "11", "Export CSV", str(csv_path),
        "11", "Import CSV", str(tmp_path / "missing.csv"),
        "11", "Import CSV", str(csv_path),
        "11", "Save (JSON)",
        "11", "Load sample data", "y",
        "0",
    ]  # fmt: skip
    app, script = make_app(tracker, answers, tmp_path)
    app.run()
    assert csv_path.exists()
    assert "CSV file not found" in script.text
    assert "Ignored 8 transaction(s) already present." in script.text
    assert "Loaded" in script.text and "sample transactions" in script.text
    assert len(app.tracker.transactions) > 100


def test_end_of_input_saves_and_exits(tracker: FinanceTracker, tmp_path: Path) -> None:
    app, script = make_app(tracker, ["1", "expense"], tmp_path)  # input ends mid-form
    app.unsaved_changes = True
    app.run()
    assert "Goodbye!" in script.text
    assert (tmp_path / "data.json").exists()


def test_run_first_time_loads_sample(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = Script(["0"])
    monkeypatch.setattr("builtins.input", script.input)
    monkeypatch.setattr("builtins.print", script.print)
    cli.run(tmp_path / "new.json")
    assert "loaded the sample data" in script.text
    assert not (tmp_path / "new.json").exists()  # nothing saved without changes


def test_run_reports_corrupted_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "data.json"
    path.write_text("{broken", encoding="utf-8")
    script = Script(["0"])
    monkeypatch.setattr("builtins.input", script.input)
    monkeypatch.setattr("builtins.print", script.print)
    cli.run(path)
    assert "was corrupted" in script.text


def test_format_helpers() -> None:
    assert cli.format_money(-1234.5) == "-$1,234.50"
    table = cli.format_table(["Name", "Amount"], [["a", "$1.00"], ["bb", "$10.00"]])
    assert table.splitlines()[2] == "a      $1.00"


def test_amount_filter_and_long_description(tracker: FinanceTracker, tmp_path: Path) -> None:
    answers = [
        "3", "Filters", "any", "", "", "", "abc", "400", "",
        "1", "expense", "12", "2025-02-02", "Groceries", "x" * 130, "short note",
        "0",
    ]  # fmt: skip
    app, script = make_app(tracker, answers, tmp_path)
    app.run()
    # Amounts >= 400 in the fixture: 3000, 1200, 3000, 1200, 420, 500.
    assert "6 result(s)" in script.text
    assert "not a number" in script.text
    assert "At most 120 characters" in script.text
    assert tracker.search("short note")[0].amount == 12


def test_budgets_listed_without_transactions(tmp_path: Path) -> None:
    tracker = FinanceTracker()
    tracker.set_budget("Groceries", 300)
    app, script = make_app(tracker, ["8", "Back", "0"], tmp_path)
    app.run()
    assert "Groceries: $300.00 per month" in script.text


def test_quit_when_save_fails_asks_first(tracker: FinanceTracker, tmp_path: Path) -> None:
    blocker = tmp_path / "file.txt"
    blocker.write_text("not a folder", encoding="utf-8")
    script = Script(["0", "n", "0", "y"])
    app = cli.ConsoleApp(tracker, blocker / "data.json", script.input, script.print)
    app.unsaved_changes = True
    app.run()
    assert script.text.count("Could not save") == 2
    assert script.text.count("Goodbye!") == 1
