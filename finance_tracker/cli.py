"""Interactive console application (``python main.py cli``).

Main elements:
    ConsoleApp: the menu loop and one method per menu action.
    prompt_* helpers: re-ask until the user types something valid.
    format_table: render rows as an aligned text table.

Input and output functions are injected (``input_func`` / ``output_func``) so the
whole menu can be driven by automated tests with a scripted list of answers.

Course concepts illustrated:
    - User input/output: ``input()`` prompts and formatted ``print()`` output.
    - Loops and decisions: ``while`` menu loop, ``if / elif`` dispatch, validation loops.
    - Functions: small reusable prompt helpers.
    - Exceptions: invalid input and file errors are caught and explained, never crash.
    - Dictionaries: menu options map a key to a label and a method.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

import pandas as pd

from finance_tracker import alerts, analytics, visualize
from finance_tracker.config import CHARTS_DIR, OUTPUT_DIR, SAMPLE_JSON, USER_DATA_FILE
from finance_tracker.exceptions import FinanceTrackerError, ValidationError
from finance_tracker.models import EXPENSE, INCOME, Transaction, parse_amount, parse_date
from finance_tracker.tracker import FinanceTracker

InputFunc = Callable[[str], str]
OutputFunc = Callable[[str], None]

LINE_WIDTH = 72
PAGE_SIZE = 15


class QuitRequested(Exception):
    """Raised when the input stream ends (Ctrl+D / Ctrl+C) to leave the menu cleanly."""


def format_money(amount: float) -> str:
    """Format a number as dollars, e.g. ``-$1,234.50``."""
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def _is_numeric(cell: str) -> bool:
    """True for cells such as ``12``, ``$1,200.00``, ``-$5.00``, ``+13.3%`` or ``-``."""
    stripped = cell.strip().lstrip("+-").lstrip("$").rstrip("%").replace(",", "")
    return cell.strip() == "-" or stripped.replace(".", "", 1).isdigit()


def format_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """Render rows as a plain-text table with aligned columns.

    Columns whose cells are all numbers (amounts, percentages, counts) are
    right-aligned so that digits line up, like in a spreadsheet.

    Args:
        headers: Column titles.
        rows: One sequence of cell values per row.

    Returns:
        The table as a multi-line string.

    Example:
        >>> print(format_table(["Name", "Total"], [["Rent", "$950.00"], ["Gym", "$25.00"]]))
        Name    Total
        ----  -------
        Rent  $950.00
        Gym    $25.00
    """
    body = [[str(c) for c in row] for row in rows]
    cells = [[str(h) for h in headers], *body]
    widths = [max(len(row[i]) for row in cells) for i in range(len(headers))]
    numeric = [bool(body) and all(_is_numeric(row[i]) for row in body) for i in range(len(headers))]

    def render(row: Sequence[str]) -> str:
        parts = [
            cell.rjust(w) if is_num else cell.ljust(w)
            for cell, w, is_num in zip(row, widths, numeric, strict=True)
        ]
        return "  ".join(parts).rstrip()

    lines = [render(row) for row in cells]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(lines)


class ConsoleApp:
    """Menu-driven console interface around a ``FinanceTracker``.

    Args:
        tracker: The data to work on.
        data_path: JSON file used by "save".
        input_func: Function used to read user input (None = built-in ``input``).
        output_func: Function used to display text (None = built-in ``print``).
        charts_dir: Where "generate charts" writes PNG files.
    """

    def __init__(
        self,
        tracker: FinanceTracker,
        data_path: Path = USER_DATA_FILE,
        input_func: InputFunc | None = None,
        output_func: OutputFunc | None = None,
        charts_dir: Path = CHARTS_DIR,
    ) -> None:
        self.tracker = tracker
        self.data_path = Path(data_path)
        # Resolved at call time, not as default arguments: defaults are evaluated once
        # when the function is defined, so a later patch of input/print would be ignored.
        self._input = input_func or input
        self.out = output_func or print
        self.charts_dir = Path(charts_dir)
        self.unsaved_changes = False
        # Concept: dictionary — each menu key maps to (label, method); adding an option
        # is one line and the dispatch code never changes.
        self.menu: dict[str, tuple[str, Callable[[], None]]] = {
            "1": ("Add a transaction", self.add_transaction),
            "2": ("List transactions", self.list_transactions),
            "3": ("Search / filter transactions", self.search_transactions),
            "4": ("Edit a transaction", self.edit_transaction),
            "5": ("Delete a transaction", self.delete_transaction),
            "6": ("Monthly spending summary", self.show_summary),
            "7": ("Spending trends & analysis", self.show_trends),
            "8": ("Budgets & alerts", self.manage_budgets),
            "9": ("Savings goals", self.manage_goals),
            "10": ("Generate charts (PNG)", self.generate_charts),
            "11": ("Save / import / export files", self.manage_files),
            "0": ("Save and quit", self.quit),
        }
        self.running = False

    # ------------------------------------------------------------------ input helpers
    def ask(self, prompt: str) -> str:
        """Read one line of input, turning end-of-input into a clean quit."""
        try:
            return self._input(prompt).strip()
        except (EOFError, KeyboardInterrupt) as exc:
            raise QuitRequested from exc

    def prompt_amount(self, prompt: str) -> float:
        """Ask for a positive amount until the answer is valid."""
        # Concept: loop + decision — re-prompt until the user enters a valid amount
        while True:
            raw = self.ask(prompt)
            try:
                return parse_amount(raw)
            except ValidationError as exc:
                self.out(f"  ✗ {exc}. Please try again.")

    def prompt_date(self, prompt: str, default: date | None = None) -> date:
        """Ask for a ``YYYY-MM-DD`` date; an empty answer returns ``default``."""
        default = default or date.today()
        while True:
            raw = self.ask(f"{prompt} [{default.isoformat()}]: ")
            if not raw:
                return default
            try:
                return parse_date(raw)
            except ValidationError as exc:
                self.out(f"  ✗ {exc}.")

    def prompt_choice(self, prompt: str, options: Sequence[str]) -> str:
        """Show numbered options and return the chosen one.

        The user may type the number or the option text (case-insensitive).
        """
        for number, option in enumerate(options, start=1):
            self.out(f"   {number:>2}. {option}")
        lookup = {option.lower(): option for option in options}
        while True:
            raw = self.ask(prompt)
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                return options[int(raw) - 1]
            if raw.lower() in lookup:
                return lookup[raw.lower()]
            self.out(f"  ✗ Please enter a number between 1 and {len(options)}.")

    def prompt_category(self, kind: str) -> str:
        """Pick an existing category or type a new one."""
        known = (
            self.tracker.expense_categories()
            if kind == EXPENSE
            else self.tracker.income_categories()
        )
        options = [*known, "New category…"]
        choice = self.prompt_choice("Category: ", options)
        while choice == "New category…":
            choice = self.ask("New category name: ")
            if not choice:
                self.out("  ✗ The name cannot be empty.")
                choice = "New category…"
        return choice

    def prompt_yes_no(self, prompt: str) -> bool:
        """Return True for y/yes, False for n/no; re-ask otherwise."""
        while True:
            raw = self.ask(f"{prompt} (y/n): ").lower()
            if raw in {"y", "yes"}:
                return True
            if raw in {"n", "no"}:
                return False
            self.out("  ✗ Please answer y or n.")

    def pick_transaction(self) -> Transaction | None:
        """Ask for a transaction id (showing the most recent ones first)."""
        recent = self.tracker.sorted_transactions()[:10]
        if not recent:
            self.out("No transactions yet.")
            return None
        self.out(self._transaction_table(recent))
        raw = self.ask("Transaction id (blank to cancel): ")
        if not raw:
            return None
        try:
            return self.tracker.get_transaction(raw)
        except FinanceTrackerError as exc:
            self.out(f"  ✗ {exc}")
            return None

    # ------------------------------------------------------------------ display helpers
    def heading(self, title: str) -> None:
        """Print a section title."""
        self.out("")
        self.out(f"=== {title} ".ljust(LINE_WIDTH, "="))

    @staticmethod
    def _transaction_table(transactions: Sequence[Transaction]) -> str:
        rows = [
            [
                t.id,
                t.date.isoformat(),
                t.kind,
                t.category,
                format_money(t.signed_amount),
                t.description[:28],
            ]
            for t in transactions
        ]
        return format_table(["ID", "Date", "Kind", "Category", "Amount", "Description"], rows)

    def show_menu(self) -> None:
        """Print the main menu with a one-line balance header."""
        self.heading("PERSONAL FINANCE TRACKER")
        self.out(
            f"Balance: {format_money(self.tracker.balance())}   "
            f"Transactions: {len(self.tracker.transactions)}   "
            f"{'(unsaved changes)' if self.unsaved_changes else ''}".rstrip()
        )
        for key, (label, _action) in self.menu.items():
            self.out(f"  {key:>2}. {label}")

    # ------------------------------------------------------------------ main loop
    def run(self) -> None:
        """Show the menu until the user quits."""
        self.running = True
        # Concept: loop — the menu repeats until "quit" sets running to False
        while self.running:
            self.show_menu()
            try:
                choice = self.ask("Choose an option: ")
                entry = self.menu.get(choice)
                # Concept: decision structure — unknown keys get a hint, not a crash
                if entry is None:
                    self.out("  ✗ Unknown option, please pick one from the menu.")
                    continue
                entry[1]()
            except QuitRequested:
                self.out("")
                self.quit()
            except FinanceTrackerError as exc:
                # Last line of defence: any app error is reported and the menu continues.
                self.out(f"  ✗ {exc}")

    # ------------------------------------------------------------------ actions
    def add_transaction(self) -> None:
        """Menu 1 — create a transaction from user input."""
        self.heading("Add a transaction")
        kind = self.prompt_choice("Type: ", [EXPENSE, INCOME])
        amount = self.prompt_amount("Amount ($): ")
        when = self.prompt_date("Date (YYYY-MM-DD)")
        category = self.prompt_category(kind)
        description = self.ask("Description (optional): ")
        transaction = self.tracker.add_transaction(when, amount, kind, category, description)
        self.unsaved_changes = True
        self.out(
            f"  ✓ Added {transaction.kind} {format_money(transaction.amount)} "
            f"in {transaction.category} (id {transaction.id})."
        )
        # Immediate feedback: warn right away if this expense pushed a budget over 80 %.
        if transaction.is_expense:
            for alert in alerts.check_budgets(self.tracker, transaction.month):
                if alert.subject == transaction.category:
                    self.out(f"  ⚠ {alert}")

    def list_transactions(self) -> None:
        """Menu 2 — show transactions page by page, newest first."""
        self.heading("Transactions (newest first)")
        transactions = self.tracker.sorted_transactions()
        if not transactions:
            self.out("No transactions yet.")
            return
        for start in range(0, len(transactions), PAGE_SIZE):
            self.out(self._transaction_table(transactions[start : start + PAGE_SIZE]))
            shown = min(start + PAGE_SIZE, len(transactions))
            if shown >= len(transactions):
                break
            more = self.ask(f"-- {shown}/{len(transactions)} shown. Enter = more, q = stop: ")
            if more.lower() == "q":
                break

    def search_transactions(self) -> None:
        """Menu 3 — text search or filter by kind, category and dates."""
        self.heading("Search / filter")
        mode = self.prompt_choice("Search by: ", ["Text", "Filters"])
        if mode == "Text":
            results = self.tracker.search(self.ask("Text to find: "))
        else:
            kind = self.prompt_choice("Kind: ", ["any", EXPENSE, INCOME])
            category = self.ask("Category (blank = all): ")
            start = self.ask("From date YYYY-MM-DD (blank = no limit): ")
            end = self.ask("To date YYYY-MM-DD (blank = no limit): ")
            results = self.tracker.filter(
                kind=None if kind == "any" else kind,
                categories=[category] if category else None,
                start=start or None,
                end=end or None,
            )
        if not results:
            self.out("No matching transactions.")
            return
        self.out(self._transaction_table(results))
        total = sum(t.signed_amount for t in results)
        self.out(f"{len(results)} result(s), net total {format_money(total)}")

    def edit_transaction(self) -> None:
        """Menu 4 — change one field of a transaction."""
        self.heading("Edit a transaction")
        transaction = self.pick_transaction()
        if transaction is None:
            return
        field_name = self.prompt_choice(
            "Field to change: ", ["amount", "date", "category", "description", "kind"]
        )
        new_value = self.ask(f"New {field_name}: ")
        try:
            self.tracker.update_transaction(transaction.id, **{field_name: new_value})
        except ValidationError as exc:
            self.out(f"  ✗ {exc} — nothing was changed.")
            return
        self.unsaved_changes = True
        self.out("  ✓ Transaction updated.")

    def delete_transaction(self) -> None:
        """Menu 5 — delete a transaction after confirmation."""
        self.heading("Delete a transaction")
        transaction = self.pick_transaction()
        if transaction is None:
            return
        if self.prompt_yes_no(f"Delete {transaction.id} ({transaction.description or '-'})?"):
            self.tracker.delete_transaction(transaction.id)
            self.unsaved_changes = True
            self.out("  ✓ Deleted.")

    def show_summary(self) -> None:
        """Menu 6 — income, expenses and category breakdown for one month."""
        self.heading("Monthly summary")
        months = self.tracker.months()
        if not months:
            self.out("No data yet.")
            return
        month = self.prompt_choice("Month: ", months[::-1])
        income = self.tracker.total(INCOME, month)
        expense = self.tracker.total(EXPENSE, month)
        self.out(f"Income:   {format_money(income):>12}")
        self.out(f"Expenses: {format_money(expense):>12}")
        self.out(f"Net:      {format_money(income - expense):>12}")
        rows = []
        for category, spent in self.tracker.spending_by_category(month).items():
            share = spent / expense if expense else 0
            bar = "█" * round(share * 30)
            rows.append([category, format_money(spent), f"{share:.1%}", bar])
        self.out(format_table(["Category", "Spent", "Share", ""], rows))

    def show_trends(self) -> None:
        """Menu 7 — pandas analysis: monthly table, trend and top expenses."""
        self.heading("Spending trends & analysis (pandas)")
        df = analytics.to_dataframe(self.tracker.transactions)
        if df.empty:
            self.out("No data yet.")
            return
        summary = analytics.monthly_summary(df)
        trend = analytics.spending_trend(df)
        rows = []
        for month, row in summary.iterrows():
            rolling = trend["rolling_avg"].get(month)
            change = trend["mom_change_pct"].get(month)  # NaN for the first month
            rows.append(
                [
                    month,
                    format_money(row["income"]),
                    format_money(row["expense"]),
                    format_money(row["net"]),
                    f"{row['savings_rate']:.1f}%",
                    format_money(rolling) if pd.notna(rolling) else "-",
                    f"{change:+.1f}%" if pd.notna(change) else "-",
                ]
            )
        self.out(
            format_table(["Month", "Income", "Expenses", "Net", "Saved", "3-mo avg", "MoM"], rows)
        )
        k = analytics.kpis(df)
        self.out(
            f"\nOverall savings rate: {k['savings_rate']:.1f}%   "
            f"Average monthly spending: {format_money(k['avg_monthly_expense'])}"
        )
        self.out("\nTop 5 expenses:")
        top = analytics.top_expenses(df, 5)
        self.out(
            format_table(
                ["Date", "Category", "Description", "Amount"],
                [
                    [r.date.date().isoformat(), r.category, r.description, format_money(r.amount)]
                    for r in top.itertuples()
                ],
            )
        )

    def manage_budgets(self) -> None:
        """Menu 8 — view budget status, set or remove a budget."""
        self.heading("Budgets & alerts")
        month = self.tracker.latest_month()
        status = alerts.check_budgets(self.tracker, month, include_ok=True)
        if status:
            self.out(f"Budget status for {month}:")
            for alert in status:
                self.out(f"  {alert}")
        else:
            self.out("No budgets defined yet.")
        for alert in alerts.check_goals(self.tracker):
            self.out(f"  {alert}")
        action = self.prompt_choice("Action: ", ["Set a budget", "Remove a budget", "Back"])
        if action == "Set a budget":
            category = self.prompt_category(EXPENSE)
            limit = self.prompt_amount("Monthly limit ($): ")
            budget = self.tracker.set_budget(category, limit)
            self.unsaved_changes = True
            self.out(f"  ✓ Budget for {budget.category}: {format_money(budget.monthly_limit)}")
        elif action == "Remove a budget":
            if not self.tracker.budgets:
                self.out("Nothing to remove.")
                return
            category = self.prompt_choice("Budget: ", sorted(self.tracker.budgets))
            self.tracker.remove_budget(category)
            self.unsaved_changes = True
            self.out("  ✓ Removed.")

    def manage_goals(self) -> None:
        """Menu 9 — list goals, add one or contribute to one."""
        self.heading("Savings goals")
        if self.tracker.goals:
            rows = [
                [
                    g.name,
                    format_money(g.saved),
                    format_money(g.target),
                    f"{g.progress:.0%}",
                    g.deadline.isoformat() if g.deadline else "-",
                ]
                for g in self.tracker.goals.values()
            ]
            self.out(format_table(["Goal", "Saved", "Target", "Progress", "Deadline"], rows))
        else:
            self.out("No savings goals yet.")
        action = self.prompt_choice("Action: ", ["Add a goal", "Contribute", "Back"])
        if action == "Add a goal":
            name = self.ask("Goal name: ")
            target = self.prompt_amount("Target amount ($): ")
            deadline_raw = self.ask("Deadline YYYY-MM-DD (optional): ")
            try:
                goal = self.tracker.add_goal(name, target, deadline=deadline_raw or None)
            except ValidationError as exc:
                self.out(f"  ✗ {exc}")
                return
            self.unsaved_changes = True
            self.out(f"  ✓ Goal '{goal.name}' created.")
        elif action == "Contribute":
            if not self.tracker.goals:
                self.out("Create a goal first.")
                return
            name = self.prompt_choice("Goal: ", list(self.tracker.goals))
            amount = self.prompt_amount("Amount to add ($): ")
            before = alerts.reached_milestone(self.tracker.goals[name].progress)
            goal = self.tracker.contribute_to_goal(name, amount)
            self.unsaved_changes = True
            self.out(f"  ✓ {goal.name}: {format_money(goal.saved)} / {format_money(goal.target)}")
            after = alerts.reached_milestone(goal.progress)
            if after is not None and after != before:
                self.out(f"  🎉 Milestone reached: {after:.0%} of your goal!")

    def generate_charts(self) -> None:
        """Menu 10 — save all charts as PNG files."""
        self.heading("Generate charts")
        df = analytics.to_dataframe(self.tracker.transactions)
        paths = visualize.save_all_charts(df, self.tracker.goals.values(), self.charts_dir)
        for path in paths:
            self.out(f"  ✓ {path}")

    def manage_files(self) -> None:
        """Menu 11 — save JSON, export CSV, import CSV or load the sample data."""
        self.heading("Files")
        action = self.prompt_choice(
            "Action: ",
            ["Save (JSON)", "Export CSV", "Import CSV", "Load sample data", "Back"],
        )
        # Concept: exception handling — a file problem is reported, the app keeps running
        try:
            if action == "Save (JSON)":
                self.save()
            elif action == "Export CSV":
                raw = self.ask(f"CSV path [{OUTPUT_DIR / 'transactions.csv'}]: ")
                path = self.tracker.export_csv(
                    Path(raw) if raw else OUTPUT_DIR / "transactions.csv"
                )
                self.out(f"  ✓ Exported {len(self.tracker.transactions)} rows to {path}")
            elif action == "Import CSV":
                path = Path(self.ask("CSV file to import: "))
                before = len(self.tracker.transactions)
                warnings = self.tracker.import_csv(path)
                for warning in warnings:
                    self.out(f"  ⚠ {warning}")
                self.unsaved_changes = True
                self.out(f"  ✓ Imported {len(self.tracker.transactions) - before} transaction(s).")
            elif action == "Load sample data" and self.prompt_yes_no(
                "Replace current data with the sample data?"
            ):
                self.tracker, _ = FinanceTracker.load_json(SAMPLE_JSON)
                self.unsaved_changes = True
                self.out(f"  ✓ Loaded {len(self.tracker.transactions)} sample transactions.")
        except FinanceTrackerError as exc:
            self.out(f"  ✗ {exc}")

    def save(self) -> None:
        """Save the tracker to the JSON data file."""
        path = self.tracker.save_json(self.data_path)
        self.unsaved_changes = False
        self.out(f"  ✓ Saved to {path}")

    def quit(self) -> None:
        """Menu 0 — save if needed, then stop the loop."""
        if self.unsaved_changes:
            try:
                self.save()
            except FinanceTrackerError as exc:
                self.out(f"  ✗ Could not save: {exc}")
        self.out("Goodbye!")
        self.running = False


def run(data_path: Path = USER_DATA_FILE) -> None:
    """Load data and start the console application.

    If ``data_path`` does not exist yet, the sample data is loaded so a first-time user
    has something to explore; it is saved to ``data_path`` only when the user saves.

    Args:
        data_path: JSON file with the user's data.
    """
    data_path = Path(data_path)
    first_run = not data_path.exists()
    tracker, warnings = FinanceTracker.load_json(data_path)
    app = ConsoleApp(tracker, data_path)
    if first_run:
        app.tracker, _ = FinanceTracker.load_json(SAMPLE_JSON)
        app.out(f"No data file yet — loaded the sample data (saved to {data_path} on save).")
    else:
        # e.g. a corrupted file that was backed up, or skipped invalid records
        for warning in warnings:
            app.out(f"⚠ {warning}")
    app.run()
