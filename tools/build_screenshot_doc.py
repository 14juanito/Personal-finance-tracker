"""Assemble the CodeStepByStep exercise screenshots into one Word document.

Reads the images in ``codestepbystep_screenshots/`` (sorted by name, 01 → 14), and
writes ``deliverables/CodeStepByStep_Screenshots.docx`` with a title page followed by
one captioned screenshot per page.

Screenshots are never generated or simulated: if the folder is missing or holds fewer
than 14 images, each missing slot becomes a clearly marked placeholder page so the
student can see exactly what still has to be added.

Usage:
    python tools/build_screenshot_doc.py [--source DIR] [--output FILE]
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "codestepbystep_screenshots"
OUTPUT_FILE = ROOT / "deliverables" / "CodeStepByStep_Screenshots.docx"
EXPECTED_COUNT = 14
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
MAX_WIDTH_IN, MAX_HEIGHT_IN = 6.5, 7.8  # usable area on US Letter with 1" margins
ACCENT = RGBColor(0x15, 0x65, 0xC0)
GREY = RGBColor(0x75, 0x75, 0x75)


def natural_key(path: Path) -> list[object]:
    """Sort key so that "2.png" comes before "10.png"."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def find_images(source: Path) -> list[Path]:
    """Return the screenshots in ``source`` sorted naturally (empty if the folder is missing)."""
    if not source.is_dir():
        return []
    return sorted(
        (p for p in source.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES), key=natural_key
    )


def caption_for(path: Path, number: int) -> str:
    """Build a caption from a file name such as ``03_list_sum.png``."""
    words = re.sub(r"^\d+[\s_-]*", "", path.stem).replace("_", " ").replace("-", " ").strip()
    return f"Exercise {number:02d}" + (f" — {words}" if words else "")


def fit_size(path: Path) -> tuple[Inches, Inches]:
    """Scale an image to fit the page while keeping its aspect ratio."""
    with Image.open(path) as image:
        width, height = image.size
    ratio = min(MAX_WIDTH_IN / width, MAX_HEIGHT_IN / height)
    return Inches(width * ratio), Inches(height * ratio)


def _page_break(document: Document) -> None:
    document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def _placeholder_box(document: Document, number: int) -> None:
    """A dashed, empty frame telling the student which screenshot is missing."""
    table = document.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.0)
    borders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        border = OxmlElement(f"w:{side}")
        border.set(qn("w:val"), "dashed")
        border.set(qn("w:sz"), "12")
        border.set(qn("w:color"), "9E9E9E")
        borders.append(border)
    cell._tc.get_or_add_tcPr().append(borders)
    for _ in range(8):
        cell.add_paragraph()
    paragraph = cell.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(f"[ PLACEHOLDER — insert CodeStepByStep screenshot #{number:02d} ]")
    run.bold = True
    run.font.color.rgb = GREY
    hint = cell.add_paragraph()
    hint.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hint_run = hint.add_run(
        f"Save it as codestepbystep_screenshots/{number:02d}_<exercise>.png "
        "and run: python tools/build_screenshot_doc.py"
    )
    hint_run.font.size = Pt(9)
    hint_run.font.color.rgb = GREY
    for _ in range(8):
        cell.add_paragraph()


def build(source: Path = SOURCE_DIR, output: Path = OUTPUT_FILE) -> tuple[Path, int, int]:
    """Create the document.

    Args:
        source: Folder with the screenshots.
        output: Destination ``.docx``.

    Returns:
        ``(output path, number of real screenshots, number of placeholders)``.
    """
    images = find_images(source)
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
    for line in (
        "DATA 333 – Data Management & Analysis",
        "Bellevue College — Prior Learning Assessment",
        "",
        "[Student Name]",
        f"[Date]   (generated {date.today():%B %d, %Y})",
    ):
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.add_run(line).font.size = Pt(12)
    total_slots = max(EXPECTED_COUNT, len(images))
    note = document.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note_run = note.add_run(
        f"{len(images)} of {EXPECTED_COUNT} screenshots included"
        + ("" if len(images) >= EXPECTED_COUNT else " — placeholders mark the missing ones")
    )
    note_run.italic, note_run.font.color.rgb = True, GREY

    # One screenshot (or placeholder) per page
    for number in range(1, total_slots + 1):
        document.add_section(WD_SECTION.NEW_PAGE)
        heading = document.add_paragraph()
        if number <= len(images):
            path = images[number - 1]
            heading_run = heading.add_run(caption_for(path, number))
            picture = document.add_paragraph()
            picture.alignment = WD_ALIGN_PARAGRAPH.CENTER
            width, height = fit_size(path)
            picture.add_run().add_picture(str(path), width=width, height=height)
            source_note = document.add_paragraph()
            source_note.alignment = WD_ALIGN_PARAGRAPH.CENTER
            source_run = source_note.add_run(f"Figure {number}: {path.name}")
            source_run.italic, source_run.font.size = True, Pt(9)
        else:
            heading_run = heading.add_run(f"Exercise {number:02d} — screenshot missing")
            _placeholder_box(document, number)
        heading_run.bold, heading_run.font.size, heading_run.font.color.rgb = True, Pt(16), ACCENT

    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    real = min(len(images), total_slots)
    return output, real, total_slots - real


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Build the CodeStepByStep screenshot document.")
    parser.add_argument("--source", type=Path, default=SOURCE_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    args = parser.parse_args(argv)
    output, real, missing = build(args.source, args.output)
    print(f"✓ {output} — {real} screenshot(s), {missing} placeholder(s)")
    if missing:
        print(f"⚠ Add the missing screenshots to {args.source} and run this script again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
