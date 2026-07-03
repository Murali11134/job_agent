"""Build ATS-friendly resumes from a plain-text daily task log.

The flow: the user keeps a free-form log of their daily tasks and workload.
An LLM (OpenAI, optional) deciphers it into a structured profile, which is
rendered as a single-column plain-text resume with standard section headings —
the format applicant tracking systems parse most reliably. Each application
gets a copy tailored to the job description, and every resume is linted with
``ats_check`` before it ships.
"""

from __future__ import annotations

import json
import os
import re
from typing import List

from resume_parser import EMAIL_PATTERN, PHONE_PATTERN, KNOWN_SKILLS
from scorer import _extract_json
from scraper import Job

DEFAULT_MODEL = "gpt-4.1-mini"

ATS_SECTIONS = ["SUMMARY", "SKILLS", "EXPERIENCE", "EDUCATION"]

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "is", "it", "its", "of", "on", "or", "our", "that", "the",
    "their", "them", "they", "this", "to", "we", "will", "with", "you",
    "your", "who", "what", "job", "role", "work", "team", "years", "must",
    "should", "strong", "good", "ability", "experience", "skills", "etc",
}

PROFILE_PROMPT = """You are a professional resume writer. Convert the user's
daily task/workload log into a resume profile. Return ONLY JSON with keys:
name (string), email (string), phone (string), title (string, a job title that
fits the work described), summary (string, 2-3 sentences, third person, no
pronouns), skills (array of strings, most relevant first), experience (array of
objects with keys: role, organization, bullets - array of achievement-oriented
bullet strings starting with action verbs, quantified where possible),
education (array of strings). Use only facts present in the log; do not invent
employers, dates, or credentials."""

TAILOR_PROMPT = """You are an ATS optimization expert. Given a resume profile
JSON and a job posting, return ONLY JSON with keys: summary (string rewritten
to target this job), skills (array reordered/reworded so terms matching the job
description come first - never invent skills not in the profile), bullets_hint
(string, one sentence of advice). Keep it truthful to the original profile."""


def _openai_json(system: str, user: str, model: str) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return _extract_json(response.output_text)


def _fallback_profile(tasklog: str) -> dict:
    """Deterministic profile extraction for offline mode."""

    email = EMAIL_PATTERN.search(tasklog)
    phone = PHONE_PATTERN.search(tasklog)
    lowered = tasklog.lower()
    skills = sorted(skill for skill in KNOWN_SKILLS if skill in lowered)
    bullets = [
        line.strip().lstrip("-*• ").strip()
        for line in tasklog.splitlines()
        if len(line.strip()) > 20 and not EMAIL_PATTERN.search(line)
    ][:12]
    first_line = tasklog.strip().splitlines()[0].strip() if tasklog.strip() else ""
    name = first_line if first_line and "@" not in first_line and len(first_line) < 60 else ""

    return {
        "name": name,
        "email": email.group(0) if email else "",
        "phone": phone.group(0) if phone else "",
        "title": "Professional",
        "summary": "Professional with hands-on experience across the responsibilities below.",
        "skills": skills,
        "experience": [
            {"role": "Current Role", "organization": "", "bullets": bullets}
        ],
        "education": [],
    }


def build_profile(tasklog: str, model: str = DEFAULT_MODEL) -> dict:
    """Decipher a daily task/workload log into a structured resume profile."""

    if not os.getenv("OPENAI_API_KEY"):
        return _fallback_profile(tasklog)
    try:
        profile = _openai_json(PROFILE_PROMPT, tasklog, model)
    except Exception:
        return _fallback_profile(tasklog)
    for key, default in _fallback_profile(tasklog).items():
        profile.setdefault(key, default)
    return profile


def job_keywords(description: str, max_keywords: int = 25) -> List[str]:
    """Meaningful, frequency-ranked keywords from a job description."""

    words = re.findall(r"[a-zA-Z][a-zA-Z+#.]{1,}", description.lower())
    counts: dict[str, int] = {}
    for word in words:
        clean = word.strip(".")
        if clean in STOPWORDS or len(clean) < 3:
            continue
        counts[clean] = counts.get(clean, 0) + 1
    ranked = sorted(counts, key=lambda word: counts[word], reverse=True)
    return ranked[:max_keywords]


def tailor_profile(profile: dict, job: Job, model: str = DEFAULT_MODEL) -> dict:
    """Return a copy of the profile tuned toward one job posting."""

    tailored = json.loads(json.dumps(profile))

    if os.getenv("OPENAI_API_KEY"):
        try:
            result = _openai_json(
                TAILOR_PROMPT,
                json.dumps(
                    {
                        "profile": profile,
                        "job": {"title": job.title, "description": job.description},
                    }
                ),
                model,
            )
            if result.get("summary"):
                tailored["summary"] = str(result["summary"])
            if isinstance(result.get("skills"), list) and result["skills"]:
                tailored["skills"] = [str(skill) for skill in result["skills"]]
            return tailored
        except Exception:
            pass

    # Offline tailoring: float skills mentioned by the job to the front.
    wanted = set(job_keywords(f"{job.title} {job.description}"))
    tailored["skills"] = sorted(
        profile.get("skills", []),
        key=lambda skill: 0 if set(skill.lower().split()) & wanted else 1,
    )
    return tailored


def render_resume(profile: dict) -> str:
    """Render a profile as a single-column, plain-text, ATS-safe resume."""

    lines: List[str] = []
    if profile.get("name"):
        lines.append(profile["name"].upper())
    if profile.get("title"):
        lines.append(profile["title"])
    contact = " | ".join(
        part for part in (profile.get("email"), profile.get("phone")) if part
    )
    if contact:
        lines.append(contact)
    lines.append("")

    lines.append("SUMMARY")
    lines.append(profile.get("summary", "").strip())
    lines.append("")

    lines.append("SKILLS")
    lines.append(", ".join(profile.get("skills", [])))
    lines.append("")

    lines.append("EXPERIENCE")
    for item in profile.get("experience", []):
        header = " - ".join(
            part for part in (item.get("role"), item.get("organization")) if part
        )
        if header:
            lines.append(header)
        for bullet in item.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")

    lines.append("EDUCATION")
    for entry in profile.get("education", []) or ["Available on request"]:
        lines.append(f"- {entry}")

    return "\n".join(lines).strip() + "\n"


def ats_check(resume_text: str, job_description: str = "") -> dict:
    """Lint a resume for ATS compatibility.

    Returns {"coverage": float 0-100, "missing_keywords": [...], "issues": [...]}.
    Coverage is the share of job-description keywords present in the resume.
    """

    issues: List[str] = []
    upper = resume_text.upper()
    for section in ATS_SECTIONS:
        if section not in upper:
            issues.append(f"Missing standard section heading: {section}")
    if "\t" in resume_text or "|  " in resume_text:
        issues.append("Possible table/column layout detected; use a single column")
    if not EMAIL_PATTERN.search(resume_text):
        issues.append("No email address found")
    if len(resume_text.split()) > 1000:
        issues.append("Resume exceeds ~2 pages of text; trim for ATS")

    keywords = job_keywords(job_description) if job_description else []
    lowered = resume_text.lower()
    missing = [keyword for keyword in keywords if keyword not in lowered]
    coverage = (
        100.0 * (len(keywords) - len(missing)) / len(keywords) if keywords else 100.0
    )

    return {
        "coverage": round(coverage, 1),
        "missing_keywords": missing,
        "issues": issues,
    }
