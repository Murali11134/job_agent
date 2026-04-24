"""Score jobs against a resume using OpenAI API (with deterministic fallback)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List

from scraper import Job


@dataclass
class ScoredJob:
    job: Job
    score: float
    reason: str


def _fallback_score(job: Job, resume_text: str) -> ScoredJob:
    """Simple keyword overlap score for offline mode."""

    resume_words = set(resume_text.lower().split())
    job_words = set(f"{job.title} {job.description}".lower().split())
    overlap = resume_words.intersection(job_words)
    score = min(100.0, 15.0 + len(overlap) * 5.0)
    reason = (
        f"Fallback score using keyword overlap ({len(overlap)} shared terms)."
    )
    return ScoredJob(job=job, score=score, reason=reason)


def score_jobs_with_openai(
    jobs: List[Job],
    resume_text: str,
    model: str = "gpt-4.1-mini",
) -> List[ScoredJob]:
    """Return jobs scored by OpenAI and sorted descending.

    Falls back to local keyword scoring if API key/client are unavailable.
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return sorted(
            [_fallback_score(job, resume_text) for job in jobs],
            key=lambda item: item.score,
            reverse=True,
        )

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    scored: List[ScoredJob] = []

    for job in jobs:
        payload = {
            "resume": resume_text[:4000],
            "job": {
                "title": job.title,
                "company": job.company,
                "description": job.description,
                "url": job.url,
            },
            "instruction": "Return ONLY JSON: {\"score\": number 0-100, \"reason\": string}",
        }

        try:
            response = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": "You are an expert recruiter."},
                    {"role": "user", "content": json.dumps(payload)},
                ],
            )
            result = json.loads(response.output_text)
            scored.append(
                ScoredJob(
                    job=job,
                    score=float(result.get("score", 0)),
                    reason=str(result.get("reason", "No reason returned.")),
                )
            )
        except Exception:
            scored.append(_fallback_score(job, resume_text))

    return sorted(scored, key=lambda item: item.score, reverse=True)
