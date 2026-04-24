"""Resume parsing utilities.

This parser is intentionally lightweight: it extracts contact data and a skills list
from plain-text resumes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"\+?[0-9][0-9\-()\s]{7,}[0-9]")

KNOWN_SKILLS = {
    "python",
    "sql",
    "pandas",
    "numpy",
    "aws",
    "docker",
    "kubernetes",
    "fastapi",
    "django",
    "flask",
    "machine learning",
    "llm",
    "openai",
    "data analysis",
    "typescript",
    "react",
    "postgresql",
}


@dataclass
class ResumeProfile:
    """Parsed resume information used for matching."""

    text: str
    email: str | None
    phone: str | None
    skills: List[str]


def _extract_skills(text: str) -> List[str]:
    lowered = text.lower()
    found = [skill for skill in KNOWN_SKILLS if skill in lowered]
    return sorted(set(found))


def parse_resume(resume_path: str) -> ResumeProfile:
    """Parse a plain-text resume file and extract profile data."""

    text = Path(resume_path).read_text(encoding="utf-8")

    email_match = EMAIL_PATTERN.search(text)
    phone_match = PHONE_PATTERN.search(text)

    return ResumeProfile(
        text=text,
        email=email_match.group(0) if email_match else None,
        phone=phone_match.group(0) if phone_match else None,
        skills=_extract_skills(text),
    )
