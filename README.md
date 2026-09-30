# 💰 Personal Finance Tracker

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-3.0-150458?logo=pandas&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.64-FF4B4B?logo=streamlit&logoColor=white)
![matplotlib](https://img.shields.io/badge/matplotlib-3.11-11557C)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-2E7D32)
![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)
![Code style](https://img.shields.io/badge/lint-ruff-D7FF64)

A Python application that tracks income and expenses, categorises transactions, follows
budgets and savings goals, and turns everything into summaries, trends and charts. The same
tested core powers **a console menu, a Tkinter desktop app and a Streamlit web dashboard**.

> Developed for **DATA 333 – Data Management & Analysis – Bellevue College**
> (Prior Learning Assessment).

![Streamlit dashboard](docs/screenshots/dashboard_overview.png)

---

## ✨ Features

| | Feature | Details |
|---|---|---|
| ➕ | **Transactions** | Add, edit, delete, text search, filters (kind, category, dates, amount). Every value is validated. |
| 🗂️ | **Categories** | Built-in expense and income categories; new names are normalised (`food` → `Food`) and stored in a set. |
| 📊 | **Summaries & trends** | Monthly income, expenses, net and savings rate; category shares; 3-month rolling average; month-over-month change; top expenses (pandas). |
| 🚦 | **Budget alerts** | Monthly limit per category: **WARNING** at 80 %, **EXCEEDED** at 100 %, raised immediately after a new expense. |
| 🎯 | **Savings goals** | Target, deadline, contributions and milestones at 25 / 50 / 75 / 100 %. |
| 💾 | **JSON + CSV storage** | Full state in JSON, transactions in CSV (import/export). Atomic writes; a corrupted file is backed up and the app still starts. |
| 📈 | **Visualisation** | matplotlib charts saved as PNG and embedded in the GUI; interactive Plotly charts in the dashboard. |

## 📸 Screenshots

| Console (CLI) | Tkinter GUI |
|---|---|
| ![CLI session](docs/screenshots/cli_session.png) | ![GUI transactions](docs/screenshots/gui_transactions.png) |
| ![CLI summary](docs/screenshots/cli_summary.png) | ![GUI summary](docs/screenshots/gui_summary.png) |

| Dashboard — Trends | Dashboard — Budgets & alerts |
|---|---|
| ![Trends](docs/screenshots/dashboard_trends.png) | ![Budgets](docs/screenshots/dashboard_budgets.png) |

All screenshots are real captures, regenerated with `python tools/capture_screenshots.py`.

## 🚀 Installation

Requires **Python 3.10+** (Tkinter is included with python.org installers; on Debian/Ubuntu
run `sudo apt install python3-tk`).

```bash
git clone https://github.com/14juanito/Personal-finance-tracker.git
cd Personal-finance-tracker
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## ▶️ Usage

### 1. Demo mode: non-interactive, runs everything

```bash
python main.py demo
```

This loads `data/sample_data.json` (311 fictional transactions, April to September 2026) and
prints the overall summary, a monthly pivot table, the category breakdown, the spending trend,
the top expenses, budget alerts and goal progress. It writes the charts to `output/charts/*.png`
and the exports to `output/demo_data.json` and `output/demo_transactions.csv`.

### 2. Console mode

```bash
python main.py cli
```

A numbered menu to add, list, search, edit and delete transactions, view monthly summaries and
pandas trends, manage budgets and goals, generate charts, and import or export files. Invalid
input is explained and asked again. On first launch the sample data is loaded; your own data is
saved to `data/my_finances.json`, which is git-ignored.

### 3. Desktop GUI (Tkinter)

```bash
python main.py gui
```

Four tabs: **Transactions** (entry form, live search, sortable table), **Summary** (KPIs,
monthly table, colour-coded alerts), **Charts** (embedded matplotlib) and **Budgets & Goals**.
The File menu handles saving and CSV import and export.

### 4. Interactive dashboard (Streamlit)

```bash
streamlit run finance_tracker/dashboard.py
```

The sidebar lets you choose the data source (sample data, your saved data, or an uploaded CSV
or JSON file) and filter by date range, category and kind. The page shows KPIs with
month-over-month deltas, Plotly charts, a category × month heatmap, budget and goal progress,
and a CSV download of the filtered rows.

Options: `--data PATH` selects the JSON file for any mode, and `--output DIR` sets the demo
output folder.

## 🗂️ Project structure

```
Personal-finance-tracker/
├── main.py                     # entry point: cli | gui | demo
├── finance_tracker/
│   ├── models.py               # Transaction, SavingsGoal, Budget (validated dataclasses)
│   ├── exceptions.py           # custom exception hierarchy
│   ├── storage.py              # JSON + CSV, atomic writes, corrupted-file recovery
│   ├── tracker.py              # FinanceTracker: list / dict / set, CRUD, search, filter
│   ├── analytics.py            # pandas: monthly summary, categories, trends, KPIs
│   ├── alerts.py               # budget thresholds, goal milestones
│   ├── visualize.py            # matplotlib charts → output/charts/*.png
│   ├── config.py               # pathlib-based project paths
│   ├── cli.py                  # console menu
│   ├── gui_tkinter.py          # Tkinter desktop app
│   └── dashboard.py            # Streamlit dashboard
├── data/                       # sample_data.json, sample_transactions.csv
├── tests/                      # pytest suite
├── tools/                      # sample data, screenshots, report/slides builders
├── docs/                       # screenshots and architecture diagram
├── deliverables/               # report, slides, video script, defence guide, source zip
└── PLAN.md · DECISIONS.md · DEV_LOG.md
```

![Architecture](docs/architecture.png)

## 🧪 Tests

```bash
pytest -q                 # run the test suite
pytest --cov              # with coverage of the finance_tracker package
ruff check . && ruff format --check .
```

The suite has more than 100 tests and about 97 % coverage of the business logic. It covers:
- nominal use;
- invalid input (amounts, dates, kinds, empty names);
- missing and corrupted files, and CSV files with missing columns or bad rows;
- every pandas calculation, checked against a hand-computed dataset;
- full scripted CLI sessions;
- a Tkinter smoke test on a real display, skipped automatically when there is none;
- a headless Streamlit `AppTest`.

## 📚 Course concepts

Every concept from the brief is labelled in the code with a `# Concept:` comment:

```bash
grep -rn "# Concept:" finance_tracker main.py
```

The concepts covered are user input and output, decision structures, loops, functions, file
handling, exceptions, lists, dictionaries, sets, OOP and pandas. The mapping table is in the
[project report](deliverables/Project_Report.docx).

## 📦 Deliverables

| File | Description |
|---|---|
| `deliverables/Project_Report.docx` | 7-page report: overview, features, concepts table, architecture, challenges, testing, lessons |
| `deliverables/Demo_Slides.pptx` | 8-slide presentation |
| `deliverables/Demo_Video_Script.md` | 4-minute narration with timestamps and an OBS checklist |
| `deliverables/Code_Defense_Guide.md` | Oral defence preparation guide (in French) |
| `deliverables/CodeStepByStep_Screenshots.docx` | CodeStepByStep exercise screenshots (from `codestepbystep_screenshots/`) |
| `deliverables/finance_tracker_source.zip` | Source code and data |

Rebuild them with `python tools/build_report.py`, `python tools/build_slides.py`,
`python tools/build_screenshot_doc.py` and `python tools/build_source_zip.py`.

---

Developed for **DATA 333 – Bellevue College**. All sample data is fictional.
