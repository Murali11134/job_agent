"""Job scrapers: LinkedIn public job search plus offline dummy data.

LinkedIn scraping uses the public "jobs-guest" endpoints (no login). Requests
are rate-limited and failures degrade gracefully. Automated *submission* of
applications is intentionally not implemented; see README.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import List

import requests
from bs4 import BeautifulSoup

LINKEDIN_SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)
LINKEDIN_POSTING_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

REQUEST_DELAY_SECONDS = 1.5
PAGE_SIZE = 25


@dataclass
class Job:
    title: str
    company: str
    description: str
    url: str
    job_id: str = ""
    location: str = ""
    posted_at: str = ""
    source: str = "dummy"

    @property
    def key(self) -> str:
        """Stable identity used for 24h deduplication."""

        if self.source != "dummy" and self.job_id:
            return f"{self.source}:{self.job_id}"
        return f"{self.title}|{self.company}".strip().lower()


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
    """Return dummy jobs with optional keyword filtering.

    A non-positive ``limit`` yields an empty list.
    """

    keyword = search.strip().lower()
    jobs = DUMMY_JOBS

    if keyword:
        jobs = [
            job
            for job in DUMMY_JOBS
            if keyword in f"{job.title} {job.description} {job.company}".lower()
        ]

    return jobs[: max(0, limit)]


def parse_search_results(html: str) -> List[Job]:
    """Parse LinkedIn guest search-result HTML into Job objects (no network)."""

    soup = BeautifulSoup(html, "html.parser")
    jobs: List[Job] = []

    for card in soup.select("li"):
        title_el = card.select_one("h3.base-search-card__title")
        company_el = card.select_one("h4.base-search-card__subtitle")
        link_el = card.select_one("a.base-card__full-link") or card.select_one("a")
        if not title_el or not link_el:
            continue

        url = (link_el.get("href") or "").split("?")[0]
        entity = card.select_one("[data-entity-urn]")
        urn = entity.get("data-entity-urn", "") if entity else ""
        id_match = re.search(r"(\d+)$", urn) or re.search(r"-(\d+)$", url)
        location_el = card.select_one("span.job-search-card__location")
        time_el = card.select_one("time")

        jobs.append(
            Job(
                title=title_el.get_text(strip=True),
                company=company_el.get_text(strip=True) if company_el else "",
                description="",
                url=url,
                job_id=id_match.group(1) if id_match else "",
                location=location_el.get_text(strip=True) if location_el else "",
                posted_at=(time_el.get("datetime") or "") if time_el else "",
                source="linkedin",
            )
        )

    return jobs


def parse_job_description(html: str) -> str:
    """Extract the plain-text description from a LinkedIn job posting page."""

    soup = BeautifulSoup(html, "html.parser")
    markup = soup.select_one("div.show-more-less-html__markup") or soup.select_one(
        "section.description"
    )
    if not markup:
        return ""
    return markup.get_text(separator="\n", strip=True)


def scrape_linkedin_jobs(
    keywords: str,
    location: str = "",
    limit: int = 25,
    fetch_descriptions: bool = True,
    session: requests.Session | None = None,
) -> List[Job]:
    """Scrape public LinkedIn job listings for the given keywords/location.

    Raises ``requests.RequestException`` if LinkedIn is unreachable so callers
    can fall back to other sources.
    """

    session = session or requests.Session()
    session.headers.setdefault("User-Agent", USER_AGENT)

    jobs: List[Job] = []
    start = 0
    while len(jobs) < limit:
        response = session.get(
            LINKEDIN_SEARCH_URL,
            params={"keywords": keywords, "location": location, "start": start},
            timeout=20,
        )
        response.raise_for_status()
        page_jobs = parse_search_results(response.text)
        if not page_jobs:
            break
        jobs.extend(page_jobs)
        start += PAGE_SIZE
        time.sleep(REQUEST_DELAY_SECONDS)

    jobs = jobs[:limit]

    if fetch_descriptions:
        for job in jobs:
            if not job.job_id:
                continue
            try:
                response = session.get(
                    LINKEDIN_POSTING_URL.format(job_id=job.job_id), timeout=20
                )
                response.raise_for_status()
                job.description = parse_job_description(response.text)
            except requests.RequestException:
                job.description = ""
            time.sleep(REQUEST_DELAY_SECONDS)

    return jobs
