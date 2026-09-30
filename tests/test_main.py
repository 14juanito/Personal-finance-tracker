"""Tests for main.py: argument parsing and the non-interactive demo mode."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import main


def test_demo_writes_charts_and_exports(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    assert main.main(["demo", "--output", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Demo complete." in out
    assert "Budget alerts" in out
    assert "[EXCEEDED]" in out
    assert len(list((tmp_path / "charts").glob("*.png"))) == 4
    assert (tmp_path / "demo_data.json").exists()
    assert (tmp_path / "demo_transactions.csv").exists()


def test_demo_with_missing_dataset(tmp_path: Path) -> None:
    lines: list[str] = []
    written = main.run_demo(tmp_path / "none.json", tmp_path, lines.append)
    assert "starting with empty data" in lines[0]
    assert "  No budgets defined." in lines
    assert len(written) == 6


def test_invalid_mode_exits_with_usage(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit) as info:
        main.main(["web"])
    assert info.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_cli_and_gui_modes_dispatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[str, Path]] = []
    monkeypatch.setattr("finance_tracker.cli.run", lambda path: calls.append(("cli", path)))
    fake_gui = type(sys)("finance_tracker.gui_tkinter")
    fake_gui.run = lambda path: calls.append(("gui", path))
    monkeypatch.setitem(sys.modules, "finance_tracker.gui_tkinter", fake_gui)
    monkeypatch.setattr("finance_tracker.gui_tkinter", fake_gui, raising=False)

    main.main(["cli", "--data", str(tmp_path / "a.json")])
    main.main(["gui", "--data", str(tmp_path / "b.json")])
    assert calls == [("cli", tmp_path / "a.json"), ("gui", tmp_path / "b.json")]
