def prompt_amount(self, prompt: str) -> float:
    # Concept: loop + decision — re-prompt until the user enters a valid amount
    while True:
        raw = self.ask(prompt)
        try:
            return parse_amount(raw)
        except ValidationError as exc:
            self.out(f"  ✗ {exc}. Please try again.")
