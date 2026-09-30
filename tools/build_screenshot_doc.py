"""Assemble the CodeStepByStep exercise screenshots into one Word document.

Reads the images in ``codestepbystep_screenshots/`` (sorted by name, 01 → 14), and
writes ``deliverables/CodeStepByStep_Screenshots.docx`` with a title page followed by
one captioned screenshot per page.

Screenshots are never generated or simulated. The build fails with a clear message
when the folder is missing or any of exercises 01–14 has no screenshot, and when a
value in ``tools/submission_config.py`` contains a template marker. An empty student
name prints a fill-in field ("Student Name: ____") to complete by hand.

Usage:
    python tools/build_screenshot_doc.py [--source DIR] [--output FILE]

Main elements:
    find_images, assign_slots, missing_slots, caption_for, build, main.

Course concepts illustrated:
    File handling, dictionaries (slot → file), regular expressions, loops.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from PIL import Image
from submission_config import (
    COURSE,
    EXPECTED_SCREENSHOTS,
    INSTITUTION,
    identity_lines,
)

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "codestepbystep_screenshots"
OUTPUT_FILE = ROOT / "deliverables" / "CodeStepByStep_Screenshots.docx"
EXPECTED_COUNT = EXPECTED_SCREENSHOTS
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
MAX_WIDTH_IN, MAX_HEIGHT_IN = 6.5, 7.8  # usable area on US Letter with 1" margins
ACCENT = RGBColor(0x15, 0x65, 0xC0)


def natural_key(path: Path) -> list[object]:
    """Sort key so that "2.png" comes before "10.png".

    Args:
        path: Image file.

    Returns:
        The name split into text and integer parts.
    """
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def find_images(source: Path) -> list[Path]:
    """Find the screenshots to include.

    Args:
        source: Folder with the images.

    Returns:
        Image files sorted naturally (empty if the folder is missing).
    """
    if not source.is_dir():
        return []
    return sorted(
        (p for p in source.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES), key=natural_key
    )


def assign_slots(images: list[Path]) -> dict[int, Path]:
    """Map exercise numbers to screenshot files.

    A file whose name starts with a number (``03_loops.png``) goes to that exercise
    slot, so one missing screenshot does not shift all the following ones. Files
    without a leading number fill the remaining free slots in sorted order.

    Args:
        images: Screenshot files, already sorted.

    Returns:
        Dictionary ``{exercise number: file}``.
    """
    slots: dict[int, Path] = {}
    unnumbered: list[Path] = []
    for path in images:
        match = re.match(r"(\d+)", path.name)
        number = int(match.group(1)) if match else 0
        if number >= 1 and number not in slots:
            slots[number] = path
        else:
            unnumbered.append(path)
    free = (n for n in range(1, EXPECTED_COUNT + len(images) + 1) if n not in slots)
    for path in unnumbered:
        slots[next(free)] = path
    return slots


def caption_for(path: Path, number: int) -> str:
    """Build a caption from a file name such as ``03_list_sum.png``.

    Args:
        path: Image file.
        number: Exercise number.

    Returns:
        A caption like ``"Exercise 03 — list sum"``.
    """
    words = re.sub(r"^\d+[\s_-]*", "", path.stem).replace("_", " ").replace("-", " ").strip()
    return f"Exercise {number:02d}" + (f" — {words}" if words else "")


def fit_size(path: Path) -> tuple[Inches, Inches]:
    """Scale an image to fit the page while keeping its aspect ratio.

    Args:
        path: Image file.

    Returns:
        ``(width, height)`` as python-docx lengths.
    """
    with Image.open(path) as image:
        width, height = image.size
    ratio = min(MAX_WIDTH_IN / width, MAX_HEIGHT_IN / height)
    return Inches(width * ratio), Inches(height * ratio)


def missing_slots(slots: dict[int, Path]) -> list[int]:
    """List the exercise numbers that have no screenshot.

    Args:
        slots: Result of ``assign_slots``.

    Returns:
        Sorted missing numbers between 1 and ``EXPECTED_COUNT``.
    """
    return [n for n in range(1, EXPECTED_COUNT + 1) if n not in slots]


def build(source: Path = SOURCE_DIR, output: Path = OUTPUT_FILE) -> tuple[Path, int]:
    """Create the document from the real screenshots.

    Args:
        source: Folder with the screenshots.
        output: Destination ``.docx``.

    Returns:
        ``(output path, number of screenshots included)``.

    Raises:
        SystemExit: If a screenshot is missing or a configured value is a placeholder;
            nothing is written in that case.
    """
    slots = assign_slots(find_images(source))
    missing = missing_slots(slots)
    if missing:
        raise SystemExit(
            f"Error: {len(missing)} of {EXPECTED_COUNT} CodeStepByStep screenshots are missing "
            f"(exercise {', '.join(f'{n:02d}' for n in missing)}). Save them in "
            f"{source} as 01_<exercise>.png … {EXPECTED_COUNT:02d}_<exercise>.png, then rerun."
        )
    student, submitted = identity_lines()

    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Inches(1))
    document.styles["Normal"].font.name = "Calibri"
    document.styles["Normal"].font.size = Pt(11)

    # Title page
    for _ in range(8):
        document.add_paragraph()
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("CodeStepByStep Exercises")
    run.bold, run.font.size, run.font.color.rgb = True, Pt(30), ACCENT
    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run("Completed Python exercise screenshots").font.size = Pt(16)
    for line in (COURSE, f"{INSTITUTION} — Prior Learning Assessment", "", student, submitted):
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.add_run(line).font.size = Pt(12)

    # One captioned screenshot per page
    for number in sorted(slots):
        path = slots[number]
        document.add_section(WD_SECTION.NEW_PAGE)
        heading = document.add_paragraph()
        heading_run = heading.add_run(caption_for(path, number))
        heading_run.bold, heading_run.font.size, heading_run.font.color.rgb = True, Pt(16), ACCENT
        picture = document.add_paragraph()
        picture.alignment = WD_ALIGN_PARAGRAPH.CENTER
        width, height = fit_size(path)
        picture.add_run().add_picture(str(path), width=width, height=height)
        source_note = document.add_paragraph()
        source_note.alignment = WD_ALIGN_PARAGRAPH.CENTER
        source_run = source_note.add_run(f"Figure {number}: {path.name}")
        source_run.italic, source_run.font.size = True, Pt(9)

    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    return output, len(slots)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Command-line arguments (None = ``sys.argv[1:]``).

    Returns:
        Process exit code (0; failures exit through ``SystemExit`` with a message).
    """
    parser = argparse.ArgumentParser(description="Build the CodeStepByStep screenshot document.")
    parser.add_argument("--source", type=Path, default=SOURCE_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    args = parser.parse_args(argv)
    output, count = build(args.source, args.output)
    print(f"✓ {output} — {count} screenshots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
