"""Job-board adapters: LinkedIn, Naukri, IIMJobs, Cutshort.

Every adapter has the same signature and returns a list of ``scraper.Job``.
Adapters must raise or return an empty list on failure — the pipeline treats
each board independently and keeps going with whatever it got.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List

import requests
from bs4 import BeautifulSoup

from scraper import Job, USER_AGENT, scrape_linkedin_jobs

NAUKRI_SEARCH_URL = "https://www.naukri.com/jobapi/v3/search"
IIMJOBS_SEARCH_URL = "https://www.iimjobs.com/search/{query}-jobs"
CUTSHORT_SEARCH_URL = "https://cutshort.io/jobs/{query}-jobs"

SourceFunc = Callable[[str, str, int], List[Job]]


def _session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def fetch_linkedin(keywords: str, location: str, limit: int) -> List[Job]:
    return scrape_linkedin_jobs(keywords=keywords, location=location, limit=limit)


def parse_naukri_results(payload: dict) -> List[Job]:
    """Convert a Naukri search API JSON payload into Job objects (no network)."""

    jobs: List[Job] = []
    for detail in payload.get("jobDetails", []):
        placeholders = {
            item.get("type"): item.get("label")
            for item in detail.get("placeholders", [])
        }
        jd_url = detail.get("jdURL", "")
        jobs.append(
            Job(
                title=detail.get("title", ""),
                company=detail.get("companyName", ""),
                description=detail.get("jobDescription", ""),
                url=f"https://www.naukri.com{jd_url}" if jd_url.startswith("/") else jd_url,
                job_id=str(detail.get("jobId", "")),
                location=placeholders.get("location", ""),
                posted_at=detail.get("footerPlaceholderLabel", ""),
                source="naukri",
            )
        )
    return jobs


def fetch_naukri(keywords: str, location: str, limit: int) -> List[Job]:
    session = _session()
    # The public search API rejects requests without these client headers,
    # and returns 406 Not Acceptable unless the Accept header asks for JSON.
    session.headers.update(
        {
            "appid": "109",
            "systemid": "Naukri",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.naukri.com/",
        }
    )
    response = session.get(
        NAUKRI_SEARCH_URL,
        params={
            "noOfResults": min(limit, 100),
            "urlType": "search_by_keyword",
            "searchType": "adv",
            "keyword": keywords,
            "location": location,
        },
        timeout=20,
    )
    response.raise_for_status()
    return parse_naukri_results(response.json())[:limit]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_iimjobs_results(html: str) -> List[Job]:
    """Best-effort parse of IIMJobs search HTML (no network).

    IIMJobs job links look like ``/j/<slug>-<digits>`` (or full URLs).
    """

    soup = BeautifulSoup(html, "html.parser")
    jobs: List[Job] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=re.compile(r"/j/[^\"]*\d+")):
        href = anchor.get("href", "")
        url = href if href.startswith("http") else f"https://www.iimjobs.com{href}"
        title = anchor.get_text(" ", strip=True)
        if not title or url in seen:
            continue
        seen.add(url)
        id_match = re.search(r"(\d+)/?$", url)
        jobs.append(
            Job(
                title=title,
                company="",
                description="",
                url=url,
                job_id=id_match.group(1) if id_match else "",
                source="iimjobs",
            )
        )
    return jobs


def fetch_iimjobs(keywords: str, location: str, limit: int) -> List[Job]:
    """EXPERIMENTAL: IIMJobs renders mostly client-side; results may be sparse."""

    session = _session()
    response = session.get(
        IIMJOBS_SEARCH_URL.format(query=_slugify(keywords)), timeout=20
    )
    response.raise_for_status()
    return parse_iimjobs_results(response.text)[:limit]


def parse_cutshort_results(html: str) -> List[Job]:
    """Best-effort parse of Cutshort listing HTML (no network).

    Cutshort job links look like ``/job/<slug>`` (or full URLs).
    """

    soup = BeautifulSoup(html, "html.parser")
    jobs: List[Job] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=re.compile(r"/job/")):
        href = anchor.get("href", "")
        url = href if href.startswith("http") else f"https://cutshort.io{href}"
        title = anchor.get_text(" ", strip=True)
        if not title or url in seen:
            continue
        seen.add(url)
        jobs.append(
            Job(
                title=title,
                company="",
                description="",
                url=url,
                job_id=url.rstrip("/").rsplit("/", 1)[-1],
                source="cutshort",
            )
        )
    return jobs


def fetch_cutshort(keywords: str, location: str, limit: int) -> List[Job]:
    """EXPERIMENTAL: Cutshort renders mostly client-side; results may be sparse."""

    session = _session()
    response = session.get(
        CUTSHORT_SEARCH_URL.format(query=_slugify(keywords)), timeout=20
    )
    response.raise_for_status()
    return parse_cutshort_results(response.text)[:limit]


SOURCES: Dict[str, SourceFunc] = {
    "linkedin": fetch_linkedin,
    "naukri": fetch_naukri,
    "iimjobs": fetch_iimjobs,
    "cutshort": fetch_cutshort,
}


def fetch_all(
    source_names: List[str],
    keywords: str,
    location: str,
    limit_per_source: int,
) -> tuple[List[Job], Dict[str, str]]:
    """Fetch from every requested board; never raise.

    Returns (jobs, errors) where errors maps board name -> failure reason.
    Duplicate postings across boards (same title+company) are collapsed.
    """

    jobs: List[Job] = []
    errors: Dict[str, str] = {}
    seen_keys: set[str] = set()
    seen_title_company: set[str] = set()

    for name in source_names:
        fetch = SOURCES.get(name)
        if fetch is None:
            errors[name] = f"unknown source '{name}'"
            continue
        try:
            fetched = fetch(keywords, location, limit_per_source)
        except Exception as error:  # noqa: BLE001 - board failures must not stop the run
            errors[name] = f"{type(error).__name__}: {error}"
            continue
        for job in fetched:
            title_company = f"{job.title}|{job.company}".strip().lower()
            if job.key in seen_keys or (job.company and title_company in seen_title_company):
                continue
            seen_keys.add(job.key)
            seen_title_company.add(title_company)
            jobs.append(job)

    return jobs, errors
