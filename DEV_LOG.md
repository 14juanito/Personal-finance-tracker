# Development Log

Real problems met during development and how they were solved. This log feeds the
"Challenges & Solutions" section of the project report.

| # | Problem | Solution |
|---|---------|----------|
| 1 | `load_csv` raised `StorageError("missing columns")` inside a `try` block that also had `except OSError`. Because `StorageError` inherits from `OSError`, the generic handler caught our own error and re-wrapped it as "Could not read CSV", hiding the real cause. | Added an explicit `except StorageError: raise` clause *before* the `OSError` clause. Lesson: exception handlers are checked in order, and subclasses are caught by parent-class handlers. |
| 2 | First `git push` failed: no HTTPS credential helper configured, and the token stored in `~/.git-credentials` was rejected by GitHub. | Verified SSH access (`ssh -T git@github.com`) and set only the push URL of `origin` to SSH. No history rewrite, no force push. |
