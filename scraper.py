"""Job scraper module with dummy data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Job:
    title: str
    company: str
    description: str
    url: str


DUMMY_JOBS: List[Job] = [
    Job(
        title="Python Backend Engineer",
        company="Acme AI",
        description="Build FastAPI services, work with PostgreSQL, Docker, and AWS.",
        url="https://example.com/jobs/1",
    ),
    Job(
        title="Data Scientist",
        company="Insight Labs",
        description="Analyze data using Python, pandas, SQL, and machine learning models.",
        url="https://example.com/jobs/2",
    ),
    Job(
        title="LLM Application Engineer",
        company="NextGen Assistants",
        description="Develop LLM features, prompt engineering workflows, and OpenAI integrations.",
        url="https://example.com/jobs/3",
    ),
    Job(
        title="Frontend Engineer",
        company="Pixel Forge",
        description="Build React and TypeScript UI experiences with strong product collaboration.",
        url="https://example.com/jobs/4",
    ),
]


def scrape_jobs(search: str = "", limit: int = 10) -> List[Job]:
    """Return dummy jobs with optional keyword filtering."""

    keyword = search.strip().lower()
    jobs = DUMMY_JOBS

    if keyword:
        jobs = [
            job
            for job in DUMMY_JOBS
            if keyword in f"{job.title} {job.description} {job.company}".lower()
        ]

    return jobs[: max(1, limit)]
