"""Tkinter desktop interface (``python main.py gui``).

Main elements:
    FinanceApp: the main window with four tabs —
        Transactions  (entry form, search/filter, sortable Treeview, delete)
        Summary       (KPIs, monthly table, alerts)
        Charts        (matplotlib figures embedded in the window)
        Budgets & Goals (set budgets, create goals, contribute)
    run: create the window and start the Tk event loop.

Course concepts illustrated:
    - OOP: the whole window is one class; widgets are attributes, callbacks are methods.
    - User input/output: form fields, message boxes, file dialogs.
    - Exceptions: invalid input is caught and shown in a dialog instead of crashing.
    - Loops and decisions: filling tables, choosing the chart to draw.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from finance_tracker import alerts, analytics, visualize
from finance_tracker.config import SAMPLE_JSON, USER_DATA_FILE
from finance_tracker.exceptions import FinanceTrackerError
from finance_tracker.models import EXPENSE, INCOME
from finance_tracker.tracker import FinanceTracker

WINDOW_TITLE = "Personal Finance Tracker"
WINDOW_SIZE = (1180, 720)
MIN_SIZE = (900, 560)
# Line height of the default font on a standard 96-dpi screen; used to detect HiDPI.
BASE_LINESPACE = 18
PAD = 6
ALL = "All"
# Concept: dictionary — chart name shown in the UI → function that draws it
CHARTS = {
    "Expenses by category": lambda df, goals, dpi: visualize.category_pie(df, dpi=dpi),
    "Monthly income vs. expenses": lambda df, goals, dpi: visualize.monthly_bars(df, dpi=dpi),
    "Spending trend": lambda df, goals, dpi: visualize.trend_line(df, dpi=dpi),
    "Savings goals": lambda df, goals, dpi: visualize.goals_progress(goals, dpi=dpi),
}
ALERT_COLORS = {"EXCEEDED": "#C62828", "WARNING": "#EF6C00", "INFO": "#1565C0", "OK": "#2E7D32"}


def money(amount: float) -> str:
    """Format a number as dollars.

    Args:
        amount: Value to format.

    Returns:
        A string such as ``-$12.50``.
    """
    return f"{'-' if amount < 0 else ''}${abs(amount):,.2f}"


# Concept: OOP (inheritance) — the window extends ttk.Frame and adds its own behaviour
class FinanceApp(ttk.Frame):
    """Main application window.

    Args:
        master: The Tk root window.
        tracker: Data to display and edit.
        data_path: JSON file used by File ▸ Save.
    """

    def __init__(self, master: tk.Tk, tracker: FinanceTracker, data_path: Path) -> None:
        """Build the window, its menu, the four tabs and the status bar.

        Args:
            master: The Tk root window.
            tracker: Data to display and edit.
            data_path: JSON file used by File ▸ Save.
        """
        super().__init__(master, padding=PAD)
        self.master = master
        self.tracker = tracker
        self.data_path = Path(data_path)
        self.unsaved = False
        self.canvas: FigureCanvasTkAgg | None = None

        master.title(WINDOW_TITLE)
        self.scale = self._configure_scaling()
        width = min(self.px(WINDOW_SIZE[0]), master.winfo_screenwidth() - 80)
        height = min(self.px(WINDOW_SIZE[1]), master.winfo_screenheight() - 120)
        master.geometry(f"{width}x{height}")
        master.minsize(min(self.px(MIN_SIZE[0]), width), min(self.px(MIN_SIZE[1]), height))
        master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.pack(fill="both", expand=True)

        self._build_menu()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self._build_transactions_tab()
        self._build_summary_tab()
        self._build_charts_tab()
        self._build_budgets_tab()
        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", pady=(PAD, 0))
        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: self.refresh())
        self.refresh()

    # ------------------------------------------------------------------ layout
    def _configure_scaling(self) -> float:
        """Adapt pixel sizes to the screen's real font size (HiDPI support).

        Tk measures widget sizes in pixels but fonts in points. On a HiDPI screen the
        fonts grow while pixel sizes do not, so Treeview rows overlap. We measure the
        actual font height and scale row heights, column widths and the window with it.

        Returns:
            The scale factor (1.0 on a standard screen).
        """
        linespace = tkfont.nametofont("TkDefaultFont").metrics("linespace")
        scale = max(1.0, linespace / BASE_LINESPACE)
        ttk.Style(self.master).configure("Treeview", rowheight=int(linespace * 1.25))
        return scale

    def px(self, pixels: int) -> int:
        """Convert a size designed for a 96-dpi screen into real pixels.

        Args:
            pixels: Size on a standard screen.

        Returns:
            The size multiplied by the HiDPI scale factor.
        """
        return int(pixels * self.scale)

    def _build_menu(self) -> None:
        """Create the File menu and the Ctrl+S shortcut."""
        menubar = tk.Menu(self.master)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save)
        file_menu.add_command(label="Open JSON…", command=self.open_json)
        file_menu.add_command(label="Import CSV…", command=self.import_csv)
        file_menu.add_command(label="Export CSV…", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Load sample data", command=self.load_sample)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        self.master.config(menu=menubar)
        self.master.bind("<Control-s>", lambda _e: self.save())

    def _build_transactions_tab(self) -> None:
        """Create the entry form, the search/filter bar and the transaction Treeview."""
        tab = ttk.Frame(self.notebook, padding=PAD)
        self.notebook.add(tab, text="Transactions")

        form = ttk.LabelFrame(tab, text="New transaction", padding=PAD)
        form.pack(side="left", fill="y", padx=(0, PAD))
        self.kind_var = tk.StringVar(value=EXPENSE)
        self.amount_var = tk.StringVar()
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.category_var = tk.StringVar()
        self.description_var = tk.StringVar()

        ttk.Label(form, text="Type").grid(row=0, column=0, sticky="w")
        kind_box = ttk.Combobox(
            form, textvariable=self.kind_var, values=[EXPENSE, INCOME], state="readonly"
        )
        kind_box.grid(row=0, column=1, pady=2)
        kind_box.bind("<<ComboboxSelected>>", lambda _e: self._update_category_choices())
        fields = [
            ("Amount ($)", self.amount_var),
            ("Date (YYYY-MM-DD)", self.date_var),
        ]
        for row, (label, var) in enumerate(fields, start=1):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w")
            ttk.Entry(form, textvariable=var, width=22).grid(row=row, column=1, pady=2)
        ttk.Label(form, text="Category").grid(row=3, column=0, sticky="w")
        # Editable combobox: pick a known category or type a new one.
        self.category_box = ttk.Combobox(form, textvariable=self.category_var, width=20)
        self.category_box.grid(row=3, column=1, pady=2)
        ttk.Label(form, text="Description").grid(row=4, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.description_var, width=22).grid(row=4, column=1, pady=2)
        ttk.Button(form, text="Add transaction", command=self.add_transaction).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(PAD, 2)
        )
        ttk.Button(form, text="Delete selected", command=self.delete_selected).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=2
        )
        self._update_category_choices()

        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True)
        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=(0, PAD))
        self.search_var = tk.StringVar()
        self.filter_kind = tk.StringVar(value=ALL)
        self.filter_category = tk.StringVar(value=ALL)
        ttk.Label(bar, text="Search").pack(side="left")
        search = ttk.Entry(bar, textvariable=self.search_var, width=24)
        search.pack(side="left", padx=PAD)
        search.bind("<KeyRelease>", lambda _e: self.refresh_transactions())
        ttk.Label(bar, text="Kind").pack(side="left")
        kind_filter = ttk.Combobox(
            bar,
            textvariable=self.filter_kind,
            values=[ALL, EXPENSE, INCOME],
            state="readonly",
            width=9,
        )
        kind_filter.pack(side="left", padx=PAD)
        ttk.Label(bar, text="Category").pack(side="left")
        self.category_filter = ttk.Combobox(
            bar, textvariable=self.filter_category, state="readonly", width=16
        )
        self.category_filter.pack(side="left", padx=PAD)
        for widget in (kind_filter, self.category_filter):
            widget.bind("<<ComboboxSelected>>", lambda _e: self.refresh_transactions())
        self.count_label = ttk.Label(bar)
        self.count_label.pack(side="right")

        columns = ("date", "kind", "category", "amount", "description", "id")
        self.tree = ttk.Treeview(right, columns=columns, show="headings", selectmode="extended")
        widths = {"date": 95, "kind": 70, "category": 130, "amount": 100, "description": 260}
        for column in columns[:-1]:
            self.tree.heading(column, text=column.title(), command=lambda c=column: self.sort_by(c))
            self.tree.column(
                column, width=self.px(widths[column]), anchor="e" if column == "amount" else "w"
            )
        # The id column stays hidden: it is only used to find the selected transaction.
        self.tree.configure(displaycolumns=columns[:-1])
        self.tree.tag_configure(INCOME, foreground="#2E7D32")
        self.tree.tag_configure(EXPENSE, foreground="#B71C1C")
        scroll = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")
        self.sort_column, self.sort_reverse = "date", True

    def _build_summary_tab(self) -> None:
        """Create the KPI boxes, the monthly table and the alert list."""
        tab = ttk.Frame(self.notebook, padding=PAD)
        self.notebook.add(tab, text="Summary")
        kpi_frame = ttk.Frame(tab)
        kpi_frame.pack(fill="x", pady=(0, PAD))
        self.kpi_vars: dict[str, tk.StringVar] = {}
        for label in ("Income", "Expenses", "Net", "Savings rate", "Avg. spend / month"):
            box = ttk.LabelFrame(kpi_frame, text=label, padding=PAD)
            box.pack(side="left", expand=True, fill="x", padx=2)
            var = tk.StringVar()
            ttk.Label(box, textvariable=var, font=("TkDefaultFont", 14, "bold")).pack()
            self.kpi_vars[label] = var

        columns = ("month", "income", "expense", "net", "rate", "trend")
        self.month_tree = ttk.Treeview(tab, columns=columns, show="headings", height=7)
        titles = ["Month", "Income", "Expenses", "Net", "Savings rate", "MoM spending"]
        for column, title in zip(columns, titles, strict=True):
            self.month_tree.heading(column, text=title)
            self.month_tree.column(
                column, anchor="e" if column != "month" else "w", width=self.px(120)
            )
        self.month_tree.pack(fill="x")

        ttk.Label(tab, text="Alerts", font=("TkDefaultFont", 11, "bold")).pack(
            anchor="w", pady=(PAD * 2, 2)
        )
        self.alert_list = tk.Listbox(tab, height=10, activestyle="none")
        self.alert_list.pack(fill="both", expand=True)

    def _build_charts_tab(self) -> None:
        """Create the chart selector, the save button and the canvas area."""
        tab = ttk.Frame(self.notebook, padding=PAD)
        self.notebook.add(tab, text="Charts")
        bar = ttk.Frame(tab)
        bar.pack(fill="x")
        self.chart_var = tk.StringVar(value=next(iter(CHARTS)))
        ttk.Label(bar, text="Chart").pack(side="left")
        chooser = ttk.Combobox(
            bar, textvariable=self.chart_var, values=list(CHARTS), state="readonly", width=30
        )
        chooser.pack(side="left", padx=PAD)
        chooser.bind("<<ComboboxSelected>>", lambda _e: self.draw_chart())
        ttk.Button(bar, text="Save all charts as PNG", command=self.save_charts).pack(side="right")
        self.chart_frame = ttk.Frame(tab)
        self.chart_frame.pack(fill="both", expand=True, pady=(PAD, 0))

    def _build_budgets_tab(self) -> None:
        """Create the budget table and form, and the savings-goal table and form."""
        tab = ttk.Frame(self.notebook, padding=PAD)
        self.notebook.add(tab, text="Budgets & Goals")
        left = ttk.LabelFrame(tab, text="Monthly budgets (latest month)", padding=PAD)
        left.pack(side="left", fill="both", expand=True, padx=(0, PAD))
        self.budget_tree = ttk.Treeview(
            left, columns=("category", "limit", "spent", "used", "status"), show="headings"
        )
        for column in ("category", "limit", "spent", "used", "status"):
            self.budget_tree.heading(column, text=column.title())
            self.budget_tree.column(
                column, width=self.px(95), anchor="w" if column == "category" else "e"
            )
        for level, color in ALERT_COLORS.items():
            self.budget_tree.tag_configure(level, foreground=color)
        self.budget_tree.pack(fill="both", expand=True)
        form = ttk.Frame(left)
        form.pack(fill="x", pady=(PAD, 0))
        self.budget_category = tk.StringVar()
        self.budget_limit = tk.StringVar()
        ttk.Label(form, text="Category").pack(side="left")
        self.budget_category_box = ttk.Combobox(form, textvariable=self.budget_category, width=16)
        self.budget_category_box.pack(side="left", padx=(2, PAD))
        ttk.Label(form, text="Limit $").pack(side="left")
        ttk.Entry(form, textvariable=self.budget_limit, width=10).pack(side="left", padx=PAD)
        ttk.Button(form, text="Set budget", command=self.set_budget).pack(side="left")

        right = ttk.LabelFrame(tab, text="Savings goals", padding=PAD)
        right.pack(side="left", fill="both", expand=True)
        self.goal_tree = ttk.Treeview(
            right, columns=("name", "saved", "target", "progress", "deadline"), show="headings"
        )
        for column in ("name", "saved", "target", "progress", "deadline"):
            self.goal_tree.heading(column, text=column.title())
            self.goal_tree.column(
                column, width=self.px(95), anchor="w" if column == "name" else "e"
            )
        self.goal_tree.pack(fill="both", expand=True)
        goal_form = ttk.Frame(right)
        goal_form.pack(fill="x", pady=(PAD, 0))
        self.goal_name = tk.StringVar()
        self.goal_amount = tk.StringVar()
        ttk.Label(goal_form, text="Name").pack(side="left")
        ttk.Entry(goal_form, textvariable=self.goal_name, width=14).pack(side="left", padx=2)
        ttk.Label(goal_form, text="Amount").pack(side="left")
        ttk.Entry(goal_form, textvariable=self.goal_amount, width=9).pack(side="left", padx=2)
        ttk.Button(goal_form, text="New goal", command=self.add_goal).pack(side="left", padx=2)
        ttk.Button(goal_form, text="Contribute", command=self.contribute).pack(side="left")

    # ------------------------------------------------------------------ refresh
    def refresh(self) -> None:
        """Redraw every tab from the tracker's current data."""
        self.refresh_transactions()
        self.refresh_summary()
        self.refresh_budgets()
        if self.notebook.index("current") == 2:  # only render charts when visible
            self.draw_chart()
        flag = "  •  unsaved changes" if self.unsaved else ""
        self.status.set(
            f"{self.data_path.name}  •  {len(self.tracker.transactions)} transactions  •  "
            f"balance {money(self.tracker.balance())}{flag}"
        )

    def _update_category_choices(self) -> None:
        """Offer expense or income categories depending on the selected type."""
        kind = self.kind_var.get()
        values = (
            self.tracker.expense_categories()
            if kind == EXPENSE
            else self.tracker.income_categories()
        )
        self.category_box.configure(values=values)

    def refresh_transactions(self) -> None:
        """Fill the Treeview with transactions matching the search and filters."""
        self.category_filter.configure(values=[ALL, *sorted(self.tracker.categories)])
        kind = self.filter_kind.get()
        category = self.filter_category.get()
        text = self.search_var.get().strip()
        rows = self.tracker.search(text) if text else list(self.tracker.transactions)
        # Concept: loop + decision — keep only rows that pass every active filter
        rows = [
            t
            for t in rows
            if (kind == ALL or t.kind == kind) and (category == ALL or t.category == category)
        ]
        key_funcs = {
            "date": lambda t: t.date,
            "kind": lambda t: t.kind,
            "category": lambda t: t.category,
            "amount": lambda t: t.amount,
            "description": lambda t: t.description.lower(),
        }
        rows.sort(key=key_funcs[self.sort_column], reverse=self.sort_reverse)
        self.tree.delete(*self.tree.get_children())
        for t in rows:
            self.tree.insert(
                "",
                "end",
                iid=t.id,
                values=(
                    t.date.isoformat(),
                    t.kind,
                    t.category,
                    money(t.amount),
                    t.description,
                    t.id,
                ),
                tags=(t.kind,),
            )
        net = sum(t.signed_amount for t in rows)
        self.count_label.configure(text=f"{len(rows)} shown  •  net {money(net)}")

    def sort_by(self, column: str) -> None:
        """Sort the table by a column; clicking the same header again reverses it.

        Args:
            column: Treeview column name, e.g. ``"amount"``.
        """
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column, self.sort_reverse = column, False
        self.refresh_transactions()

    def refresh_summary(self) -> None:
        """Update KPIs, the monthly table and the alert list."""
        df = analytics.to_dataframe(self.tracker.transactions)
        k = analytics.kpis(df)
        self.kpi_vars["Income"].set(money(k["income"]))
        self.kpi_vars["Expenses"].set(money(k["expense"]))
        self.kpi_vars["Net"].set(money(k["net"]))
        self.kpi_vars["Savings rate"].set(f"{k['savings_rate']:.1f}%")
        self.kpi_vars["Avg. spend / month"].set(money(k["avg_monthly_expense"]))

        summary = analytics.monthly_summary(df)
        trend = analytics.spending_trend(df)
        self.month_tree.delete(*self.month_tree.get_children())
        for month, row in summary.iterrows():
            change = trend["mom_change_pct"].get(month)
            self.month_tree.insert(
                "",
                "end",
                values=(
                    month,
                    money(row["income"]),
                    money(row["expense"]),
                    money(row["net"]),
                    f"{row['savings_rate']:.1f}%",
                    "-" if pd.isna(change) else f"{change:+.1f}%",
                ),
            )
        self.alert_list.delete(0, "end")
        found = alerts.collect_alerts(self.tracker)
        for index, alert in enumerate(found):
            self.alert_list.insert("end", f"  {alert}")
            self.alert_list.itemconfigure(index, foreground=ALERT_COLORS[alert.level])
        if not found:
            self.alert_list.insert("end", "  No alerts — all budgets are under 80 %.")

    def refresh_budgets(self) -> None:
        """Update the budget and goal tables."""
        self.budget_category_box.configure(values=self.tracker.expense_categories())
        self.budget_tree.delete(*self.budget_tree.get_children())
        for alert in alerts.check_budgets(self.tracker, include_ok=True):
            budget = self.tracker.budgets[alert.subject]
            spent = alert.ratio * budget.monthly_limit
            self.budget_tree.insert(
                "",
                "end",
                values=(
                    budget.category,
                    money(budget.monthly_limit),
                    money(spent),
                    f"{alert.ratio:.0%}",
                    alert.level,
                ),
                tags=(alert.level,),
            )
        self.goal_tree.delete(*self.goal_tree.get_children())
        for goal in self.tracker.goals.values():
            self.goal_tree.insert(
                "",
                "end",
                iid=goal.name,
                values=(
                    goal.name,
                    money(goal.saved),
                    money(goal.target),
                    f"{goal.progress:.0%}",
                    goal.deadline.isoformat() if goal.deadline else "-",
                ),
            )

    def draw_chart(self) -> None:
        """Render the selected chart inside the Charts tab."""
        df = analytics.to_dataframe(self.tracker.transactions)
        # Charts are sized in inches: using the screen's real dpi keeps the text readable
        # on HiDPI displays, like the rest of the interface.
        figure = CHARTS[self.chart_var.get()](df, self.tracker.goals.values(), 96 * self.scale)
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(figure, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ------------------------------------------------------------------ actions
    def _error(self, exc: Exception) -> None:
        """Show an error dialog.

        Args:
            exc: The exception whose message is displayed.
        """
        messagebox.showerror(WINDOW_TITLE, str(exc), parent=self.master)

    def _changed(self, message: str) -> None:
        """Mark the data as modified, refresh every tab and show a status message.

        Args:
            message: Short description of the change.
        """
        self.unsaved = True
        self.refresh()
        self.status.set(f"{message}  •  {self.status.get()}")

    def add_transaction(self) -> None:
        """Validate the form and add the transaction."""
        # Concept: exception handling — show validation errors in a dialog
        try:
            t = self.tracker.add_transaction(
                self.date_var.get(),
                self.amount_var.get(),
                self.kind_var.get(),
                self.category_var.get(),
                self.description_var.get(),
            )
        except FinanceTrackerError as exc:
            self._error(exc)
            return
        self.amount_var.set("")
        self.description_var.set("")
        self._update_category_choices()
        self._changed(f"Added {t.kind} {money(t.amount)} ({t.category})")
        if t.is_expense:
            for alert in alerts.check_budgets(self.tracker, t.month):
                if alert.subject == t.category:
                    messagebox.showwarning("Budget alert", alert.message, parent=self.master)

    def delete_selected(self) -> None:
        """Delete the selected rows after confirmation."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo(WINDOW_TITLE, "Select one or more rows first.", parent=self.master)
            return
        if not messagebox.askyesno(
            WINDOW_TITLE, f"Delete {len(selected)} transaction(s)?", parent=self.master
        ):
            return
        for transaction_id in selected:
            self.tracker.delete_transaction(transaction_id)
        self._changed(f"Deleted {len(selected)} transaction(s)")

    def set_budget(self) -> None:
        """Create or update a budget from the form."""
        try:
            budget = self.tracker.set_budget(self.budget_category.get(), self.budget_limit.get())
        except FinanceTrackerError as exc:
            self._error(exc)
            return
        self.budget_limit.set("")
        self._changed(f"Budget {budget.category} = {money(budget.monthly_limit)}")

    def add_goal(self) -> None:
        """Create a savings goal (amount = target)."""
        try:
            goal = self.tracker.add_goal(self.goal_name.get(), self.goal_amount.get())
        except FinanceTrackerError as exc:
            self._error(exc)
            return
        self.goal_name.set("")
        self.goal_amount.set("")
        self._changed(f"Goal '{goal.name}' created")

    def contribute(self) -> None:
        """Add the amount to the selected goal (or the goal named in the form)."""
        selected = self.goal_tree.selection()
        name = selected[0] if selected else self.goal_name.get()
        try:
            before = alerts.reached_milestone(self.tracker.goals[name].progress)
            goal = self.tracker.contribute_to_goal(name, self.goal_amount.get())
        except KeyError:
            self._error(FinanceTrackerError("Select a goal in the table first."))
            return
        except FinanceTrackerError as exc:
            self._error(exc)
            return
        self.goal_amount.set("")
        self._changed(f"{goal.name}: {money(goal.saved)} / {money(goal.target)}")
        after = alerts.reached_milestone(goal.progress)
        if after is not None and after != before:
            messagebox.showinfo(
                "Milestone", f"'{goal.name}' reached {after:.0%} of its target!", parent=self.master
            )

    def save(self) -> bool:
        """Save to the JSON data file.

        Returns:
            True on success, False if an error dialog was shown.
        """
        try:
            self.tracker.save_json(self.data_path)
        except FinanceTrackerError as exc:
            self._error(exc)
            return False
        self.unsaved = False
        self.refresh()
        self.status.set(f"Saved to {self.data_path}  •  {self.status.get()}")
        return True

    def open_json(self) -> None:
        """Replace the current data with another JSON file."""
        filename = filedialog.askopenfilename(filetypes=[("JSON", "*.json")], parent=self.master)
        if not filename:
            return
        tracker, warnings = FinanceTracker.load_json(filename)
        if warnings:
            messagebox.showwarning(WINDOW_TITLE, "\n".join(warnings[:10]), parent=self.master)
        self.tracker, self.data_path, self.unsaved = tracker, Path(filename), False
        self.refresh()

    def import_csv(self) -> None:
        """Append transactions from a CSV file."""
        filename = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")], parent=self.master)
        if not filename:
            return
        before = len(self.tracker.transactions)
        try:
            warnings = self.tracker.import_csv(filename)
        except FinanceTrackerError as exc:
            self._error(exc)
            return
        if warnings:
            messagebox.showwarning(WINDOW_TITLE, "\n".join(warnings[:10]), parent=self.master)
        self._changed(f"Imported {len(self.tracker.transactions) - before} transaction(s)")

    def export_csv(self) -> None:
        """Export all transactions to a CSV file."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")], parent=self.master
        )
        if not filename:
            return
        try:
            self.tracker.export_csv(filename)
        except FinanceTrackerError as exc:
            self._error(exc)
            return
        self.status.set(f"Exported to {filename}")

    def load_sample(self) -> None:
        """Replace the current data with the sample dataset (kept at the same save path)."""
        if self.tracker.transactions and not messagebox.askyesno(
            WINDOW_TITLE, "Replace the current data with the sample data?", parent=self.master
        ):
            return
        self.tracker, _ = FinanceTracker.load_json(SAMPLE_JSON)
        self._changed("Sample data loaded")

    def save_charts(self) -> None:
        """Write every chart as PNG into output/charts/."""
        df = analytics.to_dataframe(self.tracker.transactions)
        paths = visualize.save_all_charts(df, self.tracker.goals.values())
        self.status.set(f"Saved {len(paths)} charts to {paths[0].parent}")

    def on_close(self) -> None:
        """Offer to save unsaved changes, then close the window."""
        if self.unsaved:
            answer = messagebox.askyesnocancel(
                WINDOW_TITLE, "Save changes before quitting?", parent=self.master
            )
            if answer is None or (answer and not self.save()):
                return
        self.master.destroy()


def run(data_path: Path = USER_DATA_FILE) -> None:
    """Open the main window and start the Tk event loop.

    On first launch (no data file yet) the sample data is shown so the interface is
    not empty; it is written to ``data_path`` only when the user saves.

    Args:
        data_path: JSON file with the user's data.
    """
    data_path = Path(data_path)
    first_run = not data_path.exists()
    tracker, warnings = FinanceTracker.load_json(SAMPLE_JSON if first_run else data_path)
    root = tk.Tk()
    FinanceApp(root, tracker, data_path)
    if warnings and not first_run:
        messagebox.showwarning(WINDOW_TITLE, "\n".join(warnings[:10]), parent=root)
    root.mainloop()
