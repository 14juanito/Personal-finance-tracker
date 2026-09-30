"""Single source of truth for the submission identity used by every document builder.

Edit the values here, then rebuild the deliverables:
    python tools/build_screenshot_doc.py
    python tools/build_report.py
    python tools/build_slides.py
    python tools/build_source_zip.py

Main elements:
    STUDENT_NAME, SUBMISSION_DATE, COURSE, INSTITUTION: text printed on title pages.
    EXPECTED_SCREENSHOTS: number of CodeStepByStep screenshots the submission requires.
    require_final_identity: stops a build while the name is still a placeholder.

Course concepts illustrated:
    Functions, decision structures, exceptions (``SystemExit`` with a clear message).
"""

from __future__ import annotations

import re

STUDENT_NAME = "Juan <NOM COMPLET>"
SUBMISSION_DATE = "September 30, 2026"
COURSE = "DATA 333 – Data Management & Analysis"
INSTITUTION = "Bellevue College"
EXPECTED_SCREENSHOTS = 14

# Anything still looking like a template marker: <...>, [...] or "NOM COMPLET".
_PLACEHOLDER = re.compile(r"[<>\[\]]|NOM COMPLET", re.IGNORECASE)


def is_placeholder(value: str) -> bool:
    """Tell whether a configured value is still a template marker.

    Args:
        value: A value from this module, such as ``STUDENT_NAME``.

    Returns:
        True when the value is empty or contains ``<``, ``>``, ``[``, ``]``
        or "NOM COMPLET".
    """
    return not value.strip() or bool(_PLACEHOLDER.search(value))


def require_final_identity() -> tuple[str, str]:
    """Return the name and date, refusing to build documents with placeholders.

    Returns:
        ``(STUDENT_NAME, SUBMISSION_DATE)``.

    Raises:
        SystemExit: If either value is still a placeholder; the message says which
            file and constant to edit.
    """
    problems = [
        name
        for name, value in (("STUDENT_NAME", STUDENT_NAME), ("SUBMISSION_DATE", SUBMISSION_DATE))
        if is_placeholder(value)
    ]
    if problems:
        raise SystemExit(
            f"Error: {', '.join(problems)} in tools/submission_config.py is still a "
            f"placeholder ({STUDENT_NAME!r}). Set the real value, then rebuild."
        )
    return STUDENT_NAME, SUBMISSION_DATE
