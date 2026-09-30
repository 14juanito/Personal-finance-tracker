"""Tests for visualize.py: charts render headless and are saved as PNG.

Main elements:
    Charts render headless, are saved as PNG and label amounts correctly.

Course concepts exercised:
    Functions, file handling.
"""

from __future__ import annotations

from pathlib import Path

from matplotlib.figure import Figure

from finance_tracker import analytics, visualize
from finance_tracker.tracker import FinanceTracker

PNG_SIGNATURE = b"\x89PNG"


def test_save_all_charts(tracker: FinanceTracker, tmp_path: Path) -> None:
    df = analytics.to_dataframe(tracker.transactions)
    paths = visualize.save_all_charts(df, tracker.goals.values(), tmp_path / "charts")
    assert len(paths) == 4
    for path in paths:
        assert path.read_bytes()[:4] == PNG_SIGNATURE
        assert path.stat().st_size > 5_000


def test_charts_with_empty_data(tmp_path: Path) -> None:
    empty = analytics.to_dataframe([])
    paths = visualize.save_all_charts(empty, [], tmp_path)
    assert all(p.exists() for p in paths)


def test_pie_merges_small_categories() -> None:
    tracker = FinanceTracker()
    for index in range(10):
        tracker.add_transaction("2025-01-01", 10 + index, "expense", f"Cat {index}")
    fig = visualize.category_pie(analytics.to_dataframe(tracker.transactions))
    assert isinstance(fig, Figure)
    legend_labels = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert len(legend_labels) == visualize.MAX_PIE_SLICES
    assert legend_labels[-1].startswith("All others")


def test_goal_labels_escape_dollar_signs(tracker: FinanceTracker) -> None:
    # Two bare "$" in one label would be rendered as matplotlib math-text.
    fig = visualize.goals_progress(tracker.goals.values())
    labels = [t.get_text() for t in fig.axes[0].texts]
    assert labels == [r"55%  (\$1,100 / \$2,000)"]
