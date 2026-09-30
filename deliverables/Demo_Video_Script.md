# Demo Video Script — Personal Finance Tracker

**Course:** DATA 333 – Data Management & Analysis, Bellevue College
**Target length:** about 4 minutes (3–5 min allowed)
**Narration:** only the lines in quotes are spoken (≈ 520 words, about 130 words per minute).

---

## Before recording — setup

```bash
cd Personal-finance-tracker
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python main.py demo > /dev/null      # warm up: creates output/charts/
streamlit run finance_tracker/dashboard.py --server.headless true   # leave running, open http://localhost:8501
```

Open in advance: a terminal (font size 16+), VS Code on `finance_tracker/storage.py`, the browser tab with the dashboard, and the slide deck on slide 1.

---

## Script

### 0:00 – 0:25 · Introduction
**Screen:** Slide 1 (title), then slide 2 (overview).

> "Hi, my name is [Student Name]. This is my Personal Finance Tracker, built in Python for DATA 333 at Bellevue College. It records income and expenses, sorts them into categories, and turns them into summaries, trends, budget alerts and savings-goal progress. You can use it from a console menu, a Tkinter desktop app, or a Streamlit web dashboard."

### 0:25 – 1:05 · Demo mode
**Screen:** terminal.
**Type:** `python main.py demo`
**Action:** scroll slowly through sections 1 to 8; pause on the budget alerts.

> "Let me start with demo mode. It loads a sample dataset of three hundred and eleven fictional transactions over six months and runs every feature without asking anything. First the overall numbers: about nineteen thousand dollars of income and a savings rate near twenty percent. Next, a monthly summary built with a pandas pivot table, spending by category with groupby, and a trend with a three-month rolling average and month-over-month change. Here are the budget alerts: warning above eighty percent of a budget, exceeded above one hundred. Finally, it saves four charts as PNG files, plus JSON and CSV exports."

### 1:05 – 1:50 · Console mode
**Screen:** terminal.
**Type:** `python main.py cli` → `1` → `expense` → `abc` → `64.20` → `2026-09-28` → `Groceries` → `Farmers market` → `6` → `1` (2026-09) → `0`

> "Now the interactive console. I'll add an expense. If I type letters instead of an amount, the program explains the problem and asks again: that's a validation loop, so bad input never crashes the app. I enter sixty-four twenty, date it September twenty-eighth, and pick Groceries. Right away it warns me that this pushed my grocery budget over its limit. Option six shows the monthly summary, with each category's share of spending. When I quit, my data is saved to a JSON file."

### 1:50 – 2:30 · Tkinter GUI
**Screen:** terminal, then the GUI window.
**Type:** `python main.py gui`
**Action:** type "rent" in Search; click the **Amount** header to sort; open **Summary**, **Charts** (switch charts), **Budgets & Goals**.

> "The same features exist as a desktop app built with Tkinter. The transaction table updates as I search, and clicking a column header sorts it. The Summary tab shows key numbers, a monthly table and colour-coded alerts. The Charts tab embeds the same matplotlib charts, and in Budgets and Goals I can set limits and add money to a savings goal. When a contribution crosses twenty-five, fifty or seventy-five percent of a goal, a small message celebrates the milestone. The window also scales correctly on high-resolution screens, which was one of the bugs I had to fix."

### 2:30 – 3:15 · Streamlit dashboard
**Screen:** browser at `http://localhost:8501`.
**Action:** change the date range; remove two categories; hover a bar; open **Trends** (heatmap), **Budgets & Alerts**, **Transactions** → **Download CSV**.

> "For interactive analysis there is a Streamlit dashboard. The filters in the sidebar change everything at once: the numbers, the Plotly charts and the tables. The Trends tab shows the rolling average and a heatmap of spending by category and month. I can also upload my own CSV or JSON file, or download the filtered transactions. Because the dashboard reuses the same analytics functions as the console, the numbers always match across the three interfaces."

### 3:15 – 3:50 · Code and concepts
**Screen:** VS Code: `finance_tracker/storage.py` (the `load_json` function), then `tests/` and the terminal.
**Type:** `pytest -q` then `ruff check .`

> "Under the hood, one tested core powers all three interfaces. Every course concept is labelled in the code. Here, for example, exception handling: if the JSON file is corrupted, it's backed up and the app starts cleanly instead of crashing. The project has over one hundred and fifty automated tests, about ninety-eight percent coverage, and passes the ruff linter."

### 3:50 – 4:15 · Conclusion
**Screen:** Slide 8 (conclusion).

> "To sum up: every requirement is covered, along with all four enhancements: the Tkinter GUI, JSON and CSV storage, budget alerts and the Streamlit dashboard. My biggest lesson was that looking at the real output finds bugs tests can miss. Thank you for watching."

---

## OBS recording checklist

- [ ] **Canvas & output:** 1920×1080, 30 fps; recording format MKV (remux to MP4 afterwards), encoder x264 or hardware, quality "High".
- [ ] **Scenes:** *Screen* (Display/Window Capture) and *Slides*; switch scenes with hotkeys, not the mouse.
- [ ] **Audio:** microphone at −12 to −6 dB on the meter; add Noise Suppression (RNNoise) and a Limiter filter; desktop audio muted.
- [ ] **Screen:** close notifications (Do Not Disturb), personal tabs and bookmarks; hide the desktop; terminal and editor fonts ≥ 16 pt; cursor highlight on.
- [ ] **Data:** use only the fictional sample data — no real bank information on screen.
- [ ] **Dry run:** record 10 seconds and play it back to check audio sync and legibility.
- [ ] **During recording:** follow the timestamps; pause 1 second before each scene change so it's easy to trim.
- [ ] **After recording:** trim the start and end, check the length (3–5 min), export MP4, and watch it once in full before submitting.
