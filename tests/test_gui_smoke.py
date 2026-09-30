"""Smoke tests for the Tkinter GUI (skipped automatically when no display is available)."""

from __future__ import annotations

from pathlib import Path

import pytest

tk = pytest.importorskip("tkinter")

from finance_tracker import gui_tkinter  # noqa: E402
from finance_tracker.tracker import FinanceTracker  # noqa: E402


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available for Tkinter")
    window.withdraw()
    yield window
    window.destroy()


@pytest.fixture
def quiet_dialogs(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace blocking message boxes with a recorder."""
    shown: list[str] = []
    for name in ("showerror", "showwarning", "showinfo"):
        monkeypatch.setattr(
            gui_tkinter.messagebox, name, lambda title, msg, **_k: shown.append(msg)
        )
    monkeypatch.setattr(gui_tkinter.messagebox, "askyesno", lambda *a, **k: True)
    return shown


def test_gui_builds_and_handles_actions(
    root, quiet_dialogs: list[str], tracker: FinanceTracker, tmp_path: Path
) -> None:
    app = gui_tkinter.FinanceApp(root, tracker, tmp_path / "gui.json")
    assert len(app.tree.get_children()) == 8
    assert app.kpi_vars["Income"].get() == "$6,500.00"

    # Invalid amount → error dialog, nothing added.
    app.amount_var.set("abc")
    app.category_var.set("Groceries")
    app.add_transaction()
    assert "not a number" in quiet_dialogs[-1]
    assert len(tracker.transactions) == 8

    # Valid expense → added, and a budget alert pops up (Groceries already at 105 %).
    app.amount_var.set("25")
    app.date_var.set("2025-02-25")
    app.add_transaction()
    assert len(tracker.transactions) == 9
    assert "Groceries" in quiet_dialogs[-1]

    app.search_var.set("rent")
    app.refresh_transactions()
    assert len(app.tree.get_children()) == 2
    app.search_var.set("")
    app.sort_by("amount")

    app.tree.selection_set(app.tree.get_children()[0])
    app.delete_selected()
    assert len(tracker.transactions) == 8

    app.budget_category.set("Health")
    app.budget_limit.set("90")
    app.set_budget()
    assert tracker.budgets["Health"].monthly_limit == 90

    app.goal_name.set("Bike")
    app.goal_amount.set("300")
    app.add_goal()
    app.goal_tree.selection_set("Bike")
    app.goal_amount.set("150")
    app.contribute()
    assert tracker.goals["Bike"].saved == 150
    assert "50%" in quiet_dialogs[-1]

    for index in range(len(gui_tkinter.CHARTS)):
        app.chart_var.set(list(gui_tkinter.CHARTS)[index])
        app.draw_chart()
    assert app.canvas is not None

    assert app.save() is True
    assert (tmp_path / "gui.json").exists()
    assert app.unsaved is False
