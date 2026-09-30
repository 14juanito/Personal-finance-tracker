# Execution Plan — Personal Finance Tracker (DATA 333)

Autonomous build plan. Each phase ends with `ruff check .`, `pytest -q`, a Conventional
Commit and a push to `origin/main`.

## Phase 0 — Setup
- [x] Inspect repository and remote (empty remote, branch `main`)
- [x] Create `.venv`, install dependencies, install Playwright Chromium
- [x] Verify system tools: LibreOffice (`soffice`), poppler (`pdftoppm`, `pdfinfo`), Tkinter
- [x] First commit: `.gitignore`, README skeleton, `requirements.txt`, PLAN, DECISIONS, DEV_LOG

## Phase 1 — Core domain
- [x] `exceptions.py` — custom exception hierarchy
- [x] `models.py` — `Transaction`, `SavingsGoal`, `Budget` dataclasses with validation
- [x] Tests for models

## Phase 2 — Persistence
- [x] `storage.py` — JSON + CSV save/load, corrupted-file recovery, atomic writes
- [x] Tests: round-trips, missing files, corrupted files

## Phase 3 — Business logic
- [x] `tracker.py` — `FinanceTracker` (list / dict / set), CRUD, search, filter
- [x] `alerts.py` — budget thresholds (80 % warning, 100 % exceeded), goal milestones
- [x] Tests

## Phase 4 — Analytics & visualization
- [x] `analytics.py` — pandas monthly summary, category breakdown, trends, top expenses, savings rate
- [x] `visualize.py` — matplotlib PNG charts in `output/charts/`
- [x] Tests

## Phase 5 — Sample data
- [x] `tools/generate_sample_data.py` — ~300 realistic transactions over 6 months (seeded)
- [x] `data/sample_transactions.csv`, `data/sample_data.json`

## Phase 6 — User interfaces
- [x] `cli.py` — interactive menu
- [x] `gui_tkinter.py` — form, Treeview, summary, charts
- [x] `dashboard.py` — Streamlit filters, KPIs, Plotly charts
- [x] `main.py` — `cli` / `gui` / `demo` modes
- [x] Tests (CLI with mocked input, demo mode, GUI + Streamlit smoke tests)

## Phase 7 — Deliverables
- [x] Real screenshots: CLI (rendered terminal output), GUI (X display), Streamlit (Playwright)
- [x] `tools/build_screenshot_doc.py` → `deliverables/CodeStepByStep_Screenshots.docx`
- [x] `deliverables/Project_Report.docx` (5–8 pages, verified via PDF)
- [x] `deliverables/Demo_Slides.pptx` (6–8 slides, rendered and inspected)
- [x] `deliverables/Demo_Video_Script.md` (450–650 words)
- [x] `deliverables/Code_Defense_Guide.md` (French)
- [x] `deliverables/finance_tracker_source.zip`
- [x] Portfolio README

## Phase 8 — Quality gate
- [x] `pytest --cov` green, coverage ≥ 80 % on business logic
- [x] `ruff check .` / `ruff format --check .` clean
- [x] Independent sub-agent audit against the specification; fix findings (2 passes)
- [x] Tag `v1.0.0` and push tags
