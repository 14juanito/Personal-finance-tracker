"""Capture real screenshots of every interface into docs/figures/ (for the LaTeX documents).

Outputs (PNG, 150 dpi metadata, explicit names):
    gui_transactions.png, gui_add_form.png, gui_validation_error.png, gui_summary.png,
    gui_budgets_alerts.png, gui_savings_goals.png, gui_charts.png
        The Tkinter window driven by code (tab selection, form filling, ``update()``)
        and grabbed with ImageMagick ``import``. On Linux the window runs on a private
        Xvfb display, so only the application is captured.
    dashboard_overview.png, dashboard_filters.png, dashboard_interactive.png,
    dashboard_budgets.png
        A real Streamlit server driven by headless Chromium (Playwright, 1440x900).
    cli_demo_summary.png, cli_demo_alerts.png, cli_session_add.png, cli_session_summary.png
        The actual console output of ``python main.py demo`` and of a ``python main.py cli``
        session whose answers are typed into a pseudo-terminal (stdin), recorded with
        ``rich`` (``Console(record=True).export_svg``) and converted to PNG by Chromium.
    chart_*.png
        The four PNG charts written by demo mode into output/charts/, copied as they are.

Nothing is drawn or simulated: every pixel comes from the running application.

Usage:
    python tools/capture_screenshots.py [--only gui|dashboard|cli|charts]

Main elements:
    start_xvfb, capture_gui, capture_dashboard, run_cli_session, capture_cli,
    copy_charts, main_cli.

Course concepts illustrated:
    Functions, subprocesses and pseudo-terminals, file handling (``pathlib``, ``shutil``),
    exception handling (``try/finally`` always stops the servers it starts).
"""

from __future__ import annotations

import argparse
import contextlib
import os
import pty
import re
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path

from PIL import Image, ImageChops
from rich.console import CONSOLE_SVG_FORMAT, Console
from rich.text import Text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from finance_tracker.config import CHARTS_DIR, SAMPLE_JSON  # noqa: E402

OUT_DIR = ROOT / "docs" / "figures"
PNG_DPI = (150, 150)
XVFB_SCREEN = "1920x1200x24"
TK_SCALING = 2.0  # 144 dpi: sharper GUI text in the printed documents
VIEWPORT = {"width": 1440, "height": 900}
CONSOLE_WIDTH = 100
CONSOLE_CAPTION = "actual console output"
# Answers typed into the CLI, in order (a wrong amount first, to show validation).
CLI_ANSWERS: list[str] = [
    "1", "expense", "abc", "64.20", "2026-09-28", "Groceries", "Farmers market",
    "6", "2026-09",
    "0",
]  # fmt: skip


# --------------------------------------------------------------------------- helpers
def save_png(image: Image.Image, path: Path) -> Path:
    """Save an image as PNG with 150 dpi metadata.

    Args:
        image: The image to save.
        path: Destination file.

    Returns:
        The path written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, dpi=PNG_DPI)
    return path


def trim(image: Image.Image, margin: int = 12) -> Image.Image:
    """Crop uniform borders around the content, keeping a small margin.

    Args:
        image: Image whose top-left pixel colour is the border colour.
        margin: Pixels of border kept on each side.

    Returns:
        The cropped image.
    """
    rgb = image.convert("RGB")
    background = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
    box = ImageChops.difference(rgb, background).getbbox()
    if box is None:
        return rgb
    left, top, right, bottom = box
    return rgb.crop(
        (
            max(left - margin, 0),
            max(top - margin, 0),
            min(right + margin, rgb.width),
            min(bottom + margin, rgb.height),
        )
    )


@contextlib.contextmanager
def start_xvfb() -> Iterator[str | None]:
    """Run a private virtual X display (Linux) for the GUI captures.

    Yields:
        The display name (e.g. ``":99"``), or None when Xvfb is not installed, in
        which case the current display is used.
    """
    if sys.platform != "linux" or shutil.which("Xvfb") is None:
        yield None
        return
    read_fd, write_fd = os.pipe()
    server = subprocess.Popen(
        ["Xvfb", "-displayfd", str(write_fd), "-screen", "0", XVFB_SCREEN, "-nolisten", "tcp"],
        pass_fds=(write_fd,),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.close(write_fd)
    previous = os.environ.get("DISPLAY")
    try:
        with os.fdopen(read_fd) as pipe:
            display = f":{pipe.readline().strip()}"
        os.environ["DISPLAY"] = display
        yield display
    finally:
        server.terminate()
        server.wait(timeout=10)
        if previous is None:
            os.environ.pop("DISPLAY", None)
        else:
            os.environ["DISPLAY"] = previous


# --------------------------------------------------------------------------- GUI
def capture_gui() -> list[Path]:
    """Drive the Tkinter window by code and grab each view.

    Returns:
        Paths of the images written.

    Raises:
        RuntimeError: If ImageMagick's ``import`` command is not installed.
    """
    if shutil.which("import") is None:
        raise RuntimeError("ImageMagick 'import' is required for the GUI captures")
    written: list[Path] = []
    with start_xvfb(), tempfile.TemporaryDirectory() as tmp:
        import tkinter as tk

        from finance_tracker import gui_tkinter
        from finance_tracker.tracker import FinanceTracker

        tracker, _ = FinanceTracker.load_json(SAMPLE_JSON)
        root = tk.Tk()
        root.tk.call("tk", "scaling", TK_SCALING)
        app = gui_tkinter.FinanceApp(root, tracker, Path(tmp) / "my_finances.json")
        root.geometry("+0+0")

        def settle() -> None:
            """Let Tk finish drawing before a capture."""
            for _ in range(15):
                root.update()
                time.sleep(0.04)

        def grab(name: str, with_dialog: bool = False) -> None:
            """Capture the window (and an open dialog) to ``docs/figures/<name>``.

            The whole virtual screen is grabbed and cropped: grabbing the Tk window
            alone would miss the menu bar, which Tk draws above the client area.

            Args:
                name: Output file name.
                with_dialog: Also include the open message box (a separate window).
            """
            settle()
            shot = Path(tmp) / "screen.png"
            subprocess.run(["import", "-window", "root", str(shot)], check=True)

            def box(path: str) -> tuple[int, int, int, int]:
                """Return ``(left, top, right, bottom)`` of a Tk window on screen.

                Args:
                    path: Tk window path name, e.g. ``"."``.

                Returns:
                    The window rectangle in screen pixels.
                """
                x, y, w, h = (
                    int(root.tk.call("winfo", key, path))
                    for key in ("rootx", "rooty", "width", "height")
                )
                return x, y, x + w, y + h

            # The window sits at +0+0; its menu bar occupies the strip above rooty.
            left, top, right, bottom = 0, 0, *box(".")[2:]
            if with_dialog:
                d_left, d_top, d_right, d_bottom = box(".__tk__messagebox")
                left, top = min(left, d_left), min(top, d_top)
                right, bottom = max(right, d_right), max(bottom, d_bottom)
            image = Image.open(shot).crop((left, top, right, bottom))
            written.append(save_png(image.convert("RGB"), OUT_DIR / name))

        def while_dialog_open(name: str, action: Callable[[], None]) -> None:
            """Run an action that opens a modal dialog, capture it, then press OK.

            Args:
                name: Output file name.
                action: Callback that opens the dialog (it blocks until OK is pressed,
                    so the capture is scheduled beforehand with ``after``).
            """

            def capture_and_close() -> None:
                """Capture the screen with the dialog, then close it."""
                grab(name, with_dialog=True)
                root.tk.eval(".__tk__messagebox.ok invoke")

            root.after(600, capture_and_close)
            action()

        # 1. Transactions list
        app.notebook.select(0)
        grab("gui_transactions.png")
        # 2. Add form filled in (before clicking "Add transaction")
        app.kind_var.set("expense")
        app._update_category_choices()
        app.amount_var.set("64.20")
        app.date_var.set("2026-09-28")
        app.category_var.set("Groceries")
        app.description_var.set("Farmers market")
        grab("gui_add_form.png")
        # 3. Validation error: an invalid amount opens an error dialog
        app.amount_var.set("abc")
        while_dialog_open("gui_validation_error.png", app.add_transaction)
        app.amount_var.set("")
        app.description_var.set("")
        # 4. Summary
        app.notebook.select(1)
        grab("gui_summary.png")
        # 5. Charts
        app.notebook.select(2)
        app.chart_var.set("Expenses by category")
        app.draw_chart()
        grab("gui_charts.png")
        # 6. Budgets with EXCEEDED / WARNING rows highlighted
        app.notebook.select(3)
        grab("gui_budgets_alerts.png")
        # 7. Savings goals: a contribution crosses the 25 % milestone
        app.goal_tree.selection_set("Summer Trip")
        app.goal_amount.set("120")
        while_dialog_open("gui_savings_goals.png", app.contribute)
        root.destroy()
    return written


# --------------------------------------------------------------------------- dashboard
def _free_port() -> int:
    """Ask the operating system for an unused TCP port.

    Returns:
        A free port number for the temporary Streamlit server.
    """
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def capture_dashboard() -> list[Path]:
    """Start Streamlit, drive it with headless Chromium, then stop the server.

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

    def shot(page: object, name: str) -> None:
        """Screenshot the viewport into ``docs/figures/<name>``.

        Args:
            page: The Playwright page.
            name: Output file name.
        """
        target = Path(tempfile.gettempdir()) / name
        page.screenshot(path=str(target))
        written.append(save_png(Image.open(target).convert("RGB"), OUT_DIR / name))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            # US formatting ("$3,179.23") for an American audience; 1.5x for sharp print.
            page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1.5, locale="en-US")
            for _ in range(60):
                try:
                    page.goto(f"http://localhost:{port}")
                    break
                except Exception:  # server still starting
                    time.sleep(1)
            page.wait_for_selector("[data-testid='stMetric']", timeout=60_000)
            sidebar = page.locator("[data-testid='stSidebar']")
            # Always the sample data, even if a personal data/my_finances.json exists.
            sidebar.get_by_text("Sample data", exact=True).click()
            page.wait_for_timeout(3000)
            shot(page, "dashboard_overview.png")

            # Filters: expenses only, and two categories removed from the selection.
            sidebar.get_by_text("Expenses", exact=True).click()
            page.wait_for_timeout(1500)
            for category in ("Housing", "Education"):
                sidebar.locator(f"button[aria-label='Remove {category}']").click()
                page.wait_for_timeout(1500)
            page.wait_for_timeout(2500)
            shot(page, "dashboard_filters.png")

            # Interactive Plotly chart: hover a bar to show its tooltip.
            sidebar.get_by_text("All", exact=True).click()
            page.wait_for_timeout(2500)
            # Hover the July income bar (4th month) so Plotly shows its tooltip.
            bar = page.locator(".js-plotly-plot").first.locator(".bars .point path").nth(3)
            bar.scroll_into_view_if_needed()
            # A real mouse move: Plotly's transparent drag layer sits above the bars,
            # so Playwright's hover() (which checks the target element) is refused.
            box = bar.bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.wait_for_timeout(1500)
            shot(page, "dashboard_interactive.png")

            page.get_by_role("tab", name="Budgets & Alerts").click()
            page.wait_for_timeout(2500)
            shot(page, "dashboard_budgets.png")
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
    return written


# --------------------------------------------------------------------------- CLI
def _read_until_idle(fd: int, idle: float = 0.4, limit: float = 20.0) -> str:
    """Read from a pseudo-terminal until it stays silent for ``idle`` seconds.

    Args:
        fd: Master side of the pseudo-terminal.
        idle: Silence that marks the end of the output burst.
        limit: Maximum total wait, in seconds.

    Returns:
        The text read (possibly empty when the program has exited).
    """
    chunks: list[bytes] = []
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], idle)
        if not ready:
            break
        try:
            data = os.read(fd, 65536)
        except OSError:  # the program exited and closed the terminal
            break
        if not data:
            break
        chunks.append(data)
    return b"".join(chunks).decode("utf-8", errors="replace")


def run_cli_session(data_file: Path, answers: list[str]) -> str:
    """Run ``python main.py cli`` in a pseudo-terminal and type the answers.

    A pseudo-terminal behaves like a real one: the program reads its stdin from it
    and the terminal echoes each typed answer, so the transcript is exactly what a
    user would see on screen.

    Args:
        data_file: JSON data file for the session (a copy of the sample data).
        answers: Lines typed one after the other, each after the program goes quiet.

    Returns:
        The full console transcript.
    """
    master, slave = pty.openpty()
    env = os.environ | {"PYTHONIOENCODING": "utf-8", "COLUMNS": str(CONSOLE_WIDTH)}
    process = subprocess.Popen(
        [sys.executable, "main.py", "cli", "--data", str(data_file)],
        cwd=ROOT,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=env,
    )
    os.close(slave)
    transcript = [_read_until_idle(master)]
    for answer in answers:
        os.write(master, f"{answer}\n".encode())
        transcript.append(_read_until_idle(master))
    process.wait(timeout=20)
    os.close(master)
    return "".join(transcript).replace("\r\n", "\n").replace("\r", "")


def render_console(lines: list[str], path: Path) -> Path:
    """Record text with rich, export it to SVG and convert the SVG to PNG.

    Args:
        lines: Console lines, exactly as the program printed them.
        path: Destination PNG.

    Returns:
        The path written.
    """
    from playwright.sync_api import sync_playwright

    console = Console(record=True, width=CONSOLE_WIDTH, file=open(os.devnull, "w"))  # noqa: SIM115
    console.print(Text("\n".join(lines)), markup=False, highlight=False, crop=False)
    # Local monospace font (no download), and no imitation window buttons.
    svg_format = re.sub(r"@font-face \{\{.*?\}\}\s*", "", CONSOLE_SVG_FORMAT, flags=re.S)
    svg_format = svg_format.replace("Fira Code, monospace", "'DejaVu Sans Mono', monospace")
    svg = console.export_svg(title=CONSOLE_CAPTION, code_format=svg_format)
    svg = re.sub(r'<g transform="translate\(26,22\)">.*?</g>', "", svg, flags=re.S)
    width = float(re.search(r'viewBox="0 0 ([\d.]+)', svg).group(1))
    html = (
        "<html><body style='margin:0;background:#fff'>"
        f"<div id='s' style='width:{width}px'>{svg}</div></body></html>"
    )
    with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=2)
        page.set_content(html)
        target = Path(tmp) / "console.png"
        page.locator("#s").screenshot(path=str(target))
        browser.close()
        image = trim(Image.open(target), margin=6)
    return save_png(image, path)


def _section(lines: list[str], start: str, stop: str | None) -> list[str]:
    """Return the lines from the first one containing ``start`` up to ``stop``.

    Args:
        lines: Console lines.
        start: Text identifying the first line kept.
        stop: Text identifying the first line *not* kept (None = until the end).

    Returns:
        The selected lines.
    """
    first = next(i for i, line in enumerate(lines) if start in line)
    last = len(lines)
    if stop is not None:
        last = next(i for i, line in enumerate(lines) if i > first and stop in line)
    return lines[first:last]


def capture_cli() -> list[Path]:
    """Run the real demo and CLI commands, then render their output.

    Returns:
        Paths of the images written.
    """
    with tempfile.TemporaryDirectory() as tmp:
        demo = subprocess.run(
            [sys.executable, "main.py", "demo", "--output", tmp],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            env=os.environ | {"PYTHONIOENCODING": "utf-8"},
        ).stdout.replace(tmp, "output")
        data_file = Path(tmp) / "my_finances.json"
        shutil.copy(SAMPLE_JSON, data_file)
        session = run_cli_session(data_file, CLI_ANSWERS).replace(tmp, "data")

    demo_lines = ["$ python main.py demo", *demo.rstrip().splitlines()]
    session_lines = ["$ python main.py cli", *session.rstrip().splitlines()]
    return [
        render_console(_section(demo_lines, "$ python", "4. Spending trend"),
                       OUT_DIR / "cli_demo_summary.png"),
        render_console(_section(demo_lines, "6. Budget alerts", None),
                       OUT_DIR / "cli_demo_alerts.png"),
        render_console(_section(session_lines, "=== Add a transaction", "=== PERSONAL"),
                       OUT_DIR / "cli_session_add.png"),
        render_console(_section(session_lines, "=== Monthly summary", "=== PERSONAL"),
                       OUT_DIR / "cli_session_summary.png"),
    ]  # fmt: skip


# --------------------------------------------------------------------------- charts
def copy_charts() -> list[Path]:
    """Regenerate the demo charts, then copy the four PNG files unchanged.

    Returns:
        Paths of the copies in docs/figures/.
    """
    subprocess.run([sys.executable, "main.py", "demo"], cwd=ROOT, check=True, capture_output=True)
    written = []
    for source in sorted(CHARTS_DIR.glob("*.png")):
        target = OUT_DIR / f"chart_{source.name}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        written.append(target)
    return written


def main_cli(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Command-line arguments (None = ``sys.argv[1:]``).

    Returns:
        Process exit code (0).
    """
    parser = argparse.ArgumentParser(description="Capture real interface screenshots.")
    parser.add_argument("--only", choices=["gui", "dashboard", "cli", "charts"])
    args = parser.parse_args(argv)
    steps: dict[str, Callable[[], list[Path]]] = {
        "charts": copy_charts,
        "cli": capture_cli,
        "gui": capture_gui,
        "dashboard": capture_dashboard,
    }
    for name, step in steps.items():
        if args.only in (None, name):
            for path in step():
                print(f"✓ {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
