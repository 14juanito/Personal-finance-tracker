# Decisions

Every non-obvious choice made while building the project, with its rationale.

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Python 3.11 in a local `.venv`; code targets Python 3.10+ | 3.11 is the system interpreter; 3.10+ allows `X \| Y` type hints and `match`-free simple code. |
| 2 | `requirements.txt` lists only direct dependencies pinned with `==` | Reproducible installs for the grader without freezing transitive noise. |
| 3 | Amounts are stored as positive floats; the sign is carried by `kind` (`"income"` / `"expense"`) | Easier validation (amount > 0) and clearer for students than signed amounts. |
| 4 | Money is rounded to 2 decimals on input instead of using `Decimal` | `Decimal` complicates pandas/JSON interop; rounding at the boundary is enough for a personal tracker. |
| 5 | Dates are `datetime.date` in memory and ISO `YYYY-MM-DD` strings on disk | ISO strings sort correctly, are human readable, and parse directly with pandas. |
| 6 | JSON file holds the full state (transactions, budgets, goals); CSV holds transactions only | CSV is a flat table format — ideal for Excel/pandas export — while budgets and goals are nested data suited to JSON. |
| 7 | A corrupted JSON file is renamed to `*.corrupted-<timestamp>` and an empty state is returned | Never silently delete user data; the user can inspect the backup and the app still starts. |
| 8 | Writes go to a temporary file then `Path.replace()` | Atomic replace avoids half-written files if the program crashes during a save. |
| 9 | Budgets are monthly, per expense category | Matches how people actually budget; alerts compare the current month's spending to the limit. |
| 10 | Alert thresholds: 80 % = WARNING, 100 % = EXCEEDED; goal milestones at 25/50/75/100 % | As specified; stored as module constants so they are easy to tune. |
| 11 | Sample data generated with a fixed random seed (`42`) | Deterministic data → reproducible tests, screenshots and demo video. |
| 12 | Charts are built with `matplotlib.figure.Figure` directly (no `pyplot`) | Needs no GUI backend, so `demo` mode and tests run headless; the same Figure objects are embedded in Tkinter. It also avoids pyplot's global state leaking memory when many charts are drawn. |
| 13 | The GUI embeds matplotlib figures via `FigureCanvasTkAgg` | Reuses the same chart functions as the demo — one source of truth. |
| 14 | Coverage target (≥ 80 %) measured on business logic: models, exceptions, storage, tracker, analytics, alerts, visualize | UI modules (Tkinter/Streamlit event code) are covered by smoke tests; interactive loops are hard to unit test meaningfully. `.coveragerc`/pyproject config omits `gui_tkinter.py` and `dashboard.py`. |
| 15 | Streamlit screenshots taken with Playwright headless Chromium | As specified; real rendering of the running dashboard. |
| 16 | CLI screenshots are real terminal output (demo + scripted CLI session) rendered to PNG | There is no screenshot tool for a terminal in headless mode; the text is the genuine program output, only the rendering to image is done by a script. |
| 17 | CodeStepByStep screenshots are never fabricated | The `codestepbystep_screenshots/` folder is absent, so the DOCX contains 14 clearly labelled placeholders. |
| 18 | Push uses SSH (`git remote set-url --push origin git@github.com:…`); fetch stays HTTPS | The stored HTTPS token was rejected by GitHub ("Invalid username or token"), while the SSH key is authorised for the `14juanito` account. The remote is still `origin`/`main`; only the push transport changed. |
| 19 | Paths are centralised in `finance_tracker/config.py`; user data goes to `data/my_finances.json` (git-ignored) | Keeps the sample data pristine and guarantees personal data is never committed. |
| 20 | Pie chart keeps the 6 largest categories and merges the rest into "All others" | More than ~7 slices become unreadable. |
| 21 | Sample data covers April–September 2026 (6 months, 311 transactions, fictional student profile, ~20 % savings rate) | The first draft ended in 2025 with a negative savings rate and past goal deadlines, which made every goal "overdue" relative to today (2026-09-30). Realistic, positive-savings data gives a meaningful demo with a mix of EXCEEDED / WARNING / INFO alerts. |
