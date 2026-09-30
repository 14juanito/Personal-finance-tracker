# Development Log

Real problems met during development and how they were solved. This log feeds the
"Challenges & Solutions" section of the project report.

| # | Problem | Solution |
|---|---------|----------|
| 1 | `load_csv` raised `StorageError("missing columns")` inside a `try` block that also had `except OSError`. Because `StorageError` inherits from `OSError`, the generic handler caught our own error and re-wrapped it as "Could not read CSV", hiding the real cause. | Added an explicit `except StorageError: raise` clause *before* the `OSError` clause. Lesson: exception handlers are checked in order, and subclasses are caught by parent-class handlers. |
| 2 | First `git push` failed: no HTTPS credential helper configured, and the token stored in `~/.git-credentials` was rejected by GitHub. | Verified SSH access (`ssh -T git@github.com`) and set only the push URL of `origin` to SSH. No history rewrite, no force push. |
| 3 | The first generated sample data showed a *negative* savings rate and all three goals as "missed deadline", because incomes were too low and the data ended in 2025 while the demo runs in 2026. | Re-tuned income/expense ranges and moved the data window to Apr–Sep 2026; verified with `monthly_summary` and `collect_alerts` before committing, and added a test asserting a positive overall balance. |
| 4 | Visual check of `goals_progress.png` showed labels like "(1, 850/3,000)": the dollar signs vanished and the text was italic. Matplotlib treats text between two `$` signs as LaTeX math. | Escaped the dollar signs (`\$`) in labels that contain two amounts, and added a regression test. Negative month-over-month labels were also moved below the points so they no longer overlap the trend line. |
| 5 | CLI tests that patched `builtins.input` still tried to read the real keyboard (pytest: "reading from stdin while output is captured"). `ConsoleApp` used `input_func=input` as a default argument, and default values are evaluated once, when the function is defined. | Defaults changed to `None` and resolved inside `__init__` (`input_func or input`), so the built-in is looked up at call time. Most tests inject a scripted `input` function directly. |
