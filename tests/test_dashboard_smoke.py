"""Headless smoke test of the Streamlit dashboard using Streamlit's AppTest.

Main elements:
    The Streamlit page runs headlessly (AppTest) and reacts to filters.

Course concepts exercised:
    pandas, exception handling.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from finance_tracker.config import PROJECT_ROOT

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
DASHBOARD = str(PROJECT_ROOT / "finance_tracker" / "dashboard.py")


@pytest.fixture
def no_user_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Make sure the test only ever sees the sample data, never a real user file.
    monkeypatch.setattr("finance_tracker.config.USER_DATA_FILE", tmp_path / "none.json")


def test_dashboard_renders_without_errors(no_user_data: None) -> None:
    app = AppTest.from_file(DASHBOARD, default_timeout=60).run()
    assert not app.exception
    assert app.title[0].value.endswith("Personal Finance Dashboard")
    labels = [m.label for m in app.metric]
    assert labels[:5] == ["Income", "Expenses", "Net savings", "Savings rate", "Avg. spend / month"]
    assert len(app.tabs) == 5


def test_dashboard_filters_update_kpis(no_user_data: None) -> None:
    app = AppTest.from_file(DASHBOARD, default_timeout=60).run()
    all_expenses = app.metric[1].value
    app.sidebar.multiselect[0].set_value(["Groceries", "Salary"]).run()
    assert not app.exception
    assert app.metric[1].value != all_expenses
    app.sidebar.radio[1].set_value("Income").run()
    assert app.metric[1].value == "$0"
    app.sidebar.radio[1].set_value("Expenses").run()
    assert app.metric[3].value == "n/a"  # no savings rate without income


def test_budget_messages_escape_dollar_signs(no_user_data: None) -> None:
    app = AppTest.from_file(DASHBOARD, default_timeout=60).run()
    texts = [m.value for m in app.markdown if "EXCEEDED" in m.value]
    assert texts
    assert all("\\$" in text for text in texts)


def test_corrupted_user_file_is_reported_not_renamed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    user_file = tmp_path / "my_finances.json"
    user_file.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr("finance_tracker.config.USER_DATA_FILE", user_file)
    app = AppTest.from_file(DASHBOARD, default_timeout=60).run()
    assert not app.exception
    assert "Could not load the file" in app.error[0].value
    assert user_file.exists()  # viewing must never move the user's data


def test_negative_net_is_formatted_with_leading_minus(no_user_data: None) -> None:
    app = AppTest.from_file(DASHBOARD, default_timeout=60).run()
    app.sidebar.radio[1].set_value("Expenses").run()
    assert app.metric[2].value.startswith("-$")
