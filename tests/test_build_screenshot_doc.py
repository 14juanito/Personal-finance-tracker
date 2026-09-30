"""Tests for tools/build_screenshot_doc.py and tools/submission_config.py.

Main elements:
    Strict failures (missing screenshots, placeholder name), natural sorting, slot
    numbering and a successful build with 14 test images.

Course concepts exercised:
    File handling, dictionaries, exceptions (``SystemExit``).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from docx import Document
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import build_screenshot_doc  # noqa: E402
import submission_config  # noqa: E402


def _make_images(folder: Path, names: list[str]) -> None:
    folder.mkdir(exist_ok=True)
    for name in names:
        Image.new("RGB", (400, 300), "white").save(folder / name)


@pytest.fixture
def real_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend the student has filled in the configuration."""
    monkeypatch.setattr(submission_config, "STUDENT_NAME", "Test Student")
    monkeypatch.setattr(submission_config, "SUBMISSION_DATE", "September 30, 2026")


def test_missing_folder_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="14 of 14 CodeStepByStep screenshots are missing"):
        build_screenshot_doc.build(tmp_path / "absent", tmp_path / "doc.docx")
    assert not (tmp_path / "doc.docx").exists()


def test_one_missing_screenshot_is_named(tmp_path: Path, real_identity: None) -> None:
    names = [f"{n:02d}_ex.png" for n in range(1, 15) if n != 7]
    _make_images(tmp_path / "shots", names)
    with pytest.raises(SystemExit, match="exercise 07"):
        build_screenshot_doc.build(tmp_path / "shots", tmp_path / "doc.docx")


def test_placeholder_name_blocks_the_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(submission_config, "STUDENT_NAME", "Juan <NOM COMPLET>")
    _make_images(tmp_path / "shots", [f"{n:02d}_ex.png" for n in range(1, 15)])
    with pytest.raises(SystemExit, match="STUDENT_NAME"):
        build_screenshot_doc.build(tmp_path / "shots", tmp_path / "doc.docx")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("Juan <NOM COMPLET>", True), ("[Student Name]", True), ("", False), ("Juan Pérez", False)],
)
def test_is_placeholder(value: str, expected: bool) -> None:
    assert submission_config.is_placeholder(value) is expected


def test_full_build_with_14_screenshots(tmp_path: Path, real_identity: None) -> None:
    _make_images(tmp_path / "shots", [f"{n}_exercise_{n}.png" for n in range(1, 15)])
    out, count = build_screenshot_doc.build(tmp_path / "shots", tmp_path / "doc.docx")
    document = Document(out)
    assert count == 14
    assert len(document.inline_shapes) == 14
    text = "\n".join(p.text for p in document.paragraphs)
    assert "Test Student" in text and "September 30, 2026" in text
    assert "Exercise 02 — exercise 2" in text  # natural order: 2 before 10


def test_images_sorted_naturally_and_slots_keep_numbers(tmp_path: Path) -> None:
    source = tmp_path / "shots"
    _make_images(source, ["10_last.png", "2_second.png", "1_first_loop.png", "extra.png"])
    (source / "notes.txt").write_text("ignored", encoding="utf-8")
    images = build_screenshot_doc.find_images(source)
    assert [p.name for p in images] == [
        "1_first_loop.png",
        "2_second.png",
        "10_last.png",
        "extra.png",
    ]
    slots = build_screenshot_doc.assign_slots(images)
    assert {n: p.name for n, p in slots.items()} == {
        1: "1_first_loop.png", 2: "2_second.png", 10: "10_last.png", 3: "extra.png",
    }  # fmt: skip
    assert build_screenshot_doc.missing_slots(slots)[:2] == [4, 5]
    assert build_screenshot_doc.caption_for(images[0], 1) == "Exercise 01 — first loop"


def test_empty_name_prints_fill_in_field(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(submission_config, "STUDENT_NAME", "")
    assert submission_config.identity_lines() == (
        "Student Name: ______________________",
        submission_config.SUBMISSION_DATE,
    )
    _make_images(tmp_path / "shots", [f"{n:02d}_ex.png" for n in range(1, 15)])
    out, _count = build_screenshot_doc.build(tmp_path / "shots", tmp_path / "doc.docx")
    text = "\n".join(p.text for p in Document(out).paragraphs)
    assert "Student Name: ______________________" in text


def test_placeholder_date_blocks_the_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(submission_config, "SUBMISSION_DATE", "[Date]")
    with pytest.raises(SystemExit, match="SUBMISSION_DATE"):
        submission_config.identity_lines()
