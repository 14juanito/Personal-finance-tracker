def run(self) -> None:
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
