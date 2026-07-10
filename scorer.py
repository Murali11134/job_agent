"""Score jobs against a resume using the Anthropic API (with deterministic fallback)."""

from __future__ import annotations

import json
import os
import re
import warnings
from dataclasses import dataclass
from typing import List

from scraper import Job

DEFAULT_MODEL = "claude-opus-4-8"

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "description": "Match score from 0 to 100",
        },
        "reason": {"type": "string", "description": "One-sentence justification"},
    },
    "required": ["score", "reason"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You are an expert recruiter. Score how well the candidate's resume matches "
    "the job posting, from 0 (no fit) to 100 (perfect fit)."
)


@dataclass
class ScoredJob:
    job: Job
    score: float
    reason: str


def _extract_json(text: str) -> dict:
    """Parse a JSON object from model output, tolerating markdown fences."""

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model output: {text!r}")
    return json.loads(match.group(0))


def _fallback_score(job: Job, resume_text: str) -> ScoredJob:
    """Simple keyword overlap score for offline mode."""

    resume_words = set(resume_text.lower().split())
    job_words = set(f"{job.title} {job.description}".lower().split())
    overlap = resume_words.intersection(job_words)
    score = min(100.0, 15.0 + len(overlap) * 5.0)
    reason = f"Fallback score using keyword overlap ({len(overlap)} shared terms)."
    return ScoredJob(job=job, score=score, reason=reason)


def score_jobs_with_claude(
    jobs: List[Job],
    resume_text: str,
    model: str = DEFAULT_MODEL,
) -> List[ScoredJob]:
    """Return jobs scored by Claude and sorted descending.

    Falls back to local keyword scoring if the API key is unavailable.
    """

    if not os.getenv("ANTHROPIC_API_KEY"):
        return sorted(
            [_fallback_score(job, resume_text) for job in jobs],
            key=lambda item: item.score,
            reverse=True,
        )

    import anthropic

    client = anthropic.Anthropic()
    scored: List[ScoredJob] = []

    for job in jobs:
        payload = {
            "resume": resume_text[:4000],
            "job": {
                "title": job.title,
                "company": job.company,
                "description": job.description[:4000],
                "location": job.location,
            },
        }

        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": json.dumps(payload)}],
                output_config={
                    "format": {"type": "json_schema", "schema": SCORE_SCHEMA}
                },
            )
            text = next(
                block.text for block in response.content if block.type == "text"
            )
            result = _extract_json(text)
            scored.append(
                ScoredJob(
                    job=job,
                    score=max(0.0, min(100.0, float(result.get("score", 0)))),
                    reason=str(result.get("reason", "No reason returned.")),
                )
            )
        except Exception as error:
            warnings.warn(
                f"Claude scoring failed for {job.title!r}; using keyword fallback: {error}",
                RuntimeWarning,
                stacklevel=2,
            )
            scored.append(_fallback_score(job, resume_text))

    return sorted(scored, key=lambda item: item.score, reverse=True)
