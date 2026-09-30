# Execution Plan — Personal Finance Tracker (DATA 333)

Autonomous build plan. Each phase ends with `ruff check .`, `pytest -q`, a Conventional
Commit and a push to `origin/main`.

## Phase 0 — Setup
- [x] Inspect repository and remote (empty remote, branch `main`)
- [x] Create `.venv`, install dependencies, install Playwright Chromium
- [x] Verify system tools: LibreOffice (`soffice`), poppler (`pdftoppm`, `pdfinfo`), Tkinter
- [x] First commit: `.gitignore`, README skeleton, `requirements.txt`, PLAN, DECISIONS, DEV_LOG

## Phase 1 — Core domain
- [ ] `exceptions.py` — custom exception hierarchy
- [ ] `models.py` — `Transaction`, `SavingsGoal`, `Budget` dataclasses with validation
- [ ] Tests for models

## Phase 2 — Persistence
- [ ] `storage.py` — JSON + CSV save/load, corrupted-file recovery, atomic writes
- [ ] Tests: round-trips, missing files, corrupted files

## Phase 3 — Business logic
- [ ] `tracker.py` — `FinanceTracker` (list / dict / set), CRUD, search, filter
- [ ] `alerts.py` — budget thresholds (80 % warning, 100 % exceeded), goal milestones
- [ ] Tests

## Phase 4 — Analytics & visualization
- [ ] `analytics.py` — pandas monthly summary, category breakdown, trends, top expenses, savings rate
- [ ] `visualize.py` — matplotlib PNG charts in `output/charts/`
- [ ] Tests

## Phase 5 — Sample data
- [ ] `tools/generate_sample_data.py` — ~300 realistic transactions over 6 months (seeded)
- [ ] `data/sample_transactions.csv`, `data/sample_data.json`

## Phase 6 — User interfaces
- [ ] `cli.py` — interactive menu
- [ ] `gui_tkinter.py` — form, Treeview, summary, charts
- [ ] `dashboard.py` — Streamlit filters, KPIs, Plotly charts
- [ ] `main.py` — `cli` / `gui` / `demo` modes
- [ ] Tests (CLI with mocked input, demo mode, GUI + Streamlit smoke tests)

## Phase 7 — Deliverables
- [ ] Real screenshots: CLI (rendered terminal output), GUI (X display), Streamlit (Playwright)
- [ ] `tools/build_screenshot_doc.py` → `deliverables/CodeStepByStep_Screenshots.docx`
- [ ] `deliverables/Project_Report.docx` (5–8 pages, verified via PDF)
- [ ] `deliverables/Demo_Slides.pptx` (6–8 slides, rendered and inspected)
- [ ] `deliverables/Demo_Video_Script.md` (450–650 words)
- [ ] `deliverables/Code_Defense_Guide.md` (French)
- [ ] `deliverables/finance_tracker_source.zip`
- [ ] Portfolio README

## Phase 8 — Quality gate
- [ ] `pytest --cov` green, coverage ≥ 80 % on business logic
- [ ] `ruff check .` / `ruff format --check .` clean
- [ ] Independent sub-agent audit against the specification; fix findings
- [ ] Tag `v1.0.0` and push tags
