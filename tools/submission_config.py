"""Single source of truth for the submission identity used by every document builder.

Edit the values here, then rebuild the deliverables:
    python tools/build_screenshot_doc.py
    python tools/build_latex.py
    python tools/build_slides.py
    python tools/build_source_zip.py

Main elements:
    STUDENT_NAME, SUBMISSION_DATE, COURSE, INSTITUTION: text printed on title pages.
    BLANK_NAME_FIELD: fill-in line printed when STUDENT_NAME is left empty.
    EXPECTED_SCREENSHOTS: number of CodeStepByStep screenshots the submission requires.
    identity_lines: returns what to print, and stops a build on template markers.

Course concepts illustrated:
    Functions, decision structures, exceptions (``SystemExit`` with a clear message).
"""

from __future__ import annotations

import re

# Leave empty to print a fill-in field that the student completes by hand.
STUDENT_NAME = ""
SUBMISSION_DATE = "October 1, 2026"
COURSE = "DATA 333 – Data Management & Analysis"
INSTITUTION = "Bellevue College"
EXPECTED_SCREENSHOTS = 14
BLANK_NAME_FIELD = "Student Name: ______________________"

# Anything still looking like a template marker: <...>, [...] or "NOM COMPLET".
_PLACEHOLDER = re.compile(r"[<>\[\]]|NOM COMPLET", re.IGNORECASE)


def is_placeholder(value: str) -> bool:
    """Tell whether a configured value still contains a template marker.

    Args:
        value: A value from this module, such as ``STUDENT_NAME``.

    Returns:
        True when the value contains ``<``, ``>``, ``[``, ``]`` or "NOM COMPLET".
        An empty value is not a placeholder (see ``identity_lines``).
    """
    return bool(_PLACEHOLDER.search(value))


def identity_lines(name: str | None = None, submitted: str | None = None) -> tuple[str, str]:
    """Return the name line and date printed on every title page.

    Args:
        name: Student name (None = ``STUDENT_NAME``). An empty name becomes the
            visible fill-in field ``BLANK_NAME_FIELD``, completed by hand.
        submitted: Submission date (None = ``SUBMISSION_DATE``).

    Returns:
        ``(name line, date)``.

    Raises:
        SystemExit: If a non-empty name, or the date, still contains a template marker,
            or if the date is empty; the message says which constant to edit.
    """
    name = STUDENT_NAME if name is None else name
    submitted = SUBMISSION_DATE if submitted is None else submitted
    problems = []
    if name.strip() and is_placeholder(name):
        problems.append(f"STUDENT_NAME ({name!r})")
    if not submitted.strip() or is_placeholder(submitted):
        problems.append(f"SUBMISSION_DATE ({submitted!r})")
    if problems:
        raise SystemExit(
            f"Error: {' and '.join(problems)} in tools/submission_config.py is a placeholder. "
            "Set a real value (or leave STUDENT_NAME empty for a fill-in field), then rebuild."
        )
    return (name.strip() or BLANK_NAME_FIELD), submitted.strip()
