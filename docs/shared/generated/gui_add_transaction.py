def add_transaction(self) -> None:
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
