"""Capture real screenshots of the three interfaces for the README and the report.

Outputs (in docs/screenshots/):
    cli_demo.png          `python main.py demo` output (first part)
    cli_demo_alerts.png   `python main.py demo` output (alerts, goals, files)
    cli_session.png       an interactive CLI session (add an expense, view a summary)
    gui_*.png             the Tkinter window, one image per tab
    dashboard_*.png       the Streamlit dashboard, rendered by headless Chromium

Nothing is mocked up: the CLI images are the program's genuine text output drawn onto
an image with a monospace font (a terminal cannot be screenshotted headlessly), the GUI
images are grabbed from the X display with ImageMagick's `import`, and the dashboard
images come from Playwright driving a real Streamlit server.

Usage:
    python tools/capture_screenshots.py [--only cli|gui|dashboard]

Main elements:
    render_terminal, capture_cli, capture_gui, capture_dashboard, main_cli.

Course concepts illustrated:
    Functions, subprocesses, file handling (``pathlib``), exception handling (``try/finally``).
"""

from __future__ import annotations

import argparse
import contextlib
import io
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import matplotlib
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import main  # noqa: E402
from finance_tracker.cli import ConsoleApp  # noqa: E402
from finance_tracker.config import SAMPLE_JSON  # noqa: E402
from finance_tracker.tracker import FinanceTracker  # noqa: E402

OUT_DIR = ROOT / "docs" / "screenshots"
FONT_PATH = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSansMono.ttf"
BG, FG, PROMPT = "#1E1E1E", "#D4D4D4", "#4EC9B0"
FONT_SIZE, LINE_HEIGHT, MARGIN = 15, 20, 18


def render_terminal(lines: list[str], path: Path, title: str) -> Path:
    """Draw text lines on a dark, terminal-like canvas.

    Args:
        lines: Text to draw (typed user answers start with "> ").
        path: Destination PNG.
        title: Window title shown in the fake title bar.

    Returns:
        The path written.
    """
    # Some outputs (tables) are multi-line strings: draw them line by line.
    lines = [part for line in lines for part in line.split("\n")]
    font = ImageFont.truetype(str(FONT_PATH), FONT_SIZE)
    char_width = font.getlength("M")
    width = int(max(len(line) for line in lines) * char_width) + 2 * MARGIN
    height = len(lines) * LINE_HEIGHT + 2 * MARGIN + 30
    image = Image.new("RGB", (max(width, 700), height), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, image.width, 30], fill="#333333")
    for index, color in enumerate(("#FF5F56", "#FFBD2E", "#27C93F")):
        draw.ellipse([12 + index * 22, 9, 24 + index * 22, 21], fill=color)
    draw.text((90, 7), title, font=font, fill="#BBBBBB")
    y = 30 + MARGIN
    for line in lines:
        is_prompt = line.startswith("$ ") or "▸" in line
        draw.text((MARGIN, y), line, font=font, fill=PROMPT if is_prompt else FG)
        y += LINE_HEIGHT
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path


def capture_cli() -> list[Path]:
    """Run demo mode and a scripted CLI session; render both outputs.

    Returns:
        Paths of the images written.
    """
    written: list[Path] = []
    with tempfile.TemporaryDirectory() as tmp:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main.main(["demo", "--output", tmp])
    demo_lines = ["$ python main.py demo", *buffer.getvalue().splitlines()]
    # Hide the machine-specific temp folder; the real default is output/.
    demo_lines = [line.replace(tmp, "output") for line in demo_lines]
    split = next(i for i, line in enumerate(demo_lines) if "5. Top 5" in line)
    written.append(render_terminal(demo_lines[:split], OUT_DIR / "cli_demo.png", "Terminal"))
    written.append(render_terminal(demo_lines[split:], OUT_DIR / "cli_demo_alerts.png", "Terminal"))

    # Interactive session: typed answers are echoed after each prompt, as in a terminal.
    answers = iter(["1", "expense", "abc", "64.20", "2026-09-28", "Groceries", "Farmers market",
                    "6", "2026-09", "0"])  # fmt: skip
    lines = ["$ python main.py cli"]

    def scripted_input(prompt: str) -> str:
        """Answer the next prompt and echo it, like a terminal shows typed text.

        Args:
            prompt: Prompt printed by the application.

        Returns:
            The next scripted answer.
        """
        answer = next(answers)
        lines.append(f"{prompt}{answer}")
        return answer

    with tempfile.TemporaryDirectory() as tmp:
        tracker, _ = FinanceTracker.load_json(SAMPLE_JSON)
        app = ConsoleApp(tracker, Path(tmp) / "session.json", scripted_input, lines.append)
        app.run()
        lines = [part.replace(tmp, "data") for line in lines for part in line.split("\n")]
    # Two focused images: adding an expense (with validation + budget alert), then the
    # monthly summary. The repeated main menu in between is left out.
    alert_line = next(i for i, line in enumerate(lines) if "[EXCEEDED]" in line)
    summary_start = next(i for i, line in enumerate(lines) if "=== Monthly summary" in line)
    summary_end = next(
        i for i, line in enumerate(lines) if i > summary_start and "=== PERSONAL" in line
    )
    written.append(
        render_terminal(lines[: alert_line + 1], OUT_DIR / "cli_session.png", "Terminal — CLI mode")
    )
    written.append(
        render_terminal(
            ["Choose an option: 6", *lines[summary_start:summary_end]],
            OUT_DIR / "cli_summary.png",
            "Terminal — CLI mode",
        )
    )
    return written


def capture_gui() -> list[Path]:
    """Open the Tkinter window on the current display and grab each tab.

    Returns:
        Paths of the images written.

    Raises:
        RuntimeError: If ImageMagick's ``import`` command is not installed.
    """
    import tkinter as tk

    from finance_tracker import gui_tkinter

    if shutil.which("import") is None:
        raise RuntimeError("ImageMagick 'import' is required for GUI screenshots")
    written: list[Path] = []
    with tempfile.TemporaryDirectory() as tmp:
        tracker, _ = FinanceTracker.load_json(SAMPLE_JSON)
        root = tk.Tk()
        app = gui_tkinter.FinanceApp(root, tracker, Path(tmp) / "my_finances.json")
        root.geometry("+40+40")
        names = ["transactions", "summary", "charts", "budgets_goals"]
        for index, name in enumerate(names):
            app.notebook.select(index)
            if name == "charts":
                app.chart_var.set("Monthly income vs. expenses")
                app.draw_chart()
            for _ in range(20):  # let Tk finish drawing
                root.update()
                time.sleep(0.05)
            path = OUT_DIR / f"gui_{name}.png"
            window_id = root.wm_frame()  # outer window, including the title bar
            subprocess.run(["import", "-window", window_id, str(path)], check=True)
            written.append(path)
        root.destroy()
    return written


def _free_port() -> int:
    """Ask the operating system for an unused TCP port.

    Returns:
        A free port number for the temporary Streamlit server.
    """
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def capture_dashboard() -> list[Path]:
    """Start Streamlit, then screenshot each tab with headless Chromium.

    Returns:
        Paths of the images written.
    """
    from playwright.sync_api import sync_playwright

    port = _free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "finance_tracker" / "dashboard.py"),
         "--server.headless", "true", "--server.port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )  # fmt: skip
    written: list[Path] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            for _ in range(60):
                try:
                    page.goto(f"http://localhost:{port}")
                    break
                except Exception:  # server not ready yet
                    time.sleep(1)
            page.wait_for_selector("[data-testid='stMetric']", timeout=60_000)
            page.wait_for_timeout(3000)
            tabs = {
                "Overview": "dashboard_overview.png",
                "Trends": "dashboard_trends.png",
                "Budgets & Alerts": "dashboard_budgets.png",
                "Savings Goals": "dashboard_goals.png",
            }
            for tab, filename in tabs.items():
                page.get_by_role("tab", name=tab).click()
                page.wait_for_timeout(2500)
                path = OUT_DIR / filename
                page.screenshot(path=str(path))
                written.append(path)
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
    return written


def main_cli(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Command-line arguments (None = ``sys.argv[1:]``).

    Returns:
        Process exit code (0).
    """
    parser = argparse.ArgumentParser(description="Capture interface screenshots.")
    parser.add_argument("--only", choices=["cli", "gui", "dashboard"])
    args = parser.parse_args(argv)
    steps = {"cli": capture_cli, "gui": capture_gui, "dashboard": capture_dashboard}
    for name, step in steps.items():
        if args.only in (None, name):
            for path in step():
                print(f"✓ {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
