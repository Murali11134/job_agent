"""SQLite persistence: 24-hour job deduplication and application history."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

from scraper import Job

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    job_key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_key TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT NOT NULL,
    score REAL NOT NULL,
    reason TEXT NOT NULL,
    resume_path TEXT NOT NULL,
    ats_coverage REAL NOT NULL,
    prepared_at TEXT NOT NULL
);
"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ApplicationRecord:
    job_key: str
    title: str
    company: str
    url: str
    score: float
    reason: str
    resume_path: str
    ats_coverage: float
    prepared_at: str


class JobStore:
    def __init__(self, path: str = "job_agent.db") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def filter_unseen(
        self,
        jobs: List[Job],
        within_hours: int = 24,
        limit: int | None = None,
    ) -> List[Job]:
        """Drop jobs already seen within the window; mark the rest as seen now.

        A job that reappears after the window is treated as new again. When a
        limit is supplied, later jobs are left untouched for a future run.
        """

        now = _utcnow()
        cutoff = now - timedelta(hours=within_hours)
        fresh: List[Job] = []

        for job in jobs:
            if limit is not None and len(fresh) >= limit:
                break
            row = self._conn.execute(
                "SELECT last_seen FROM seen_jobs WHERE job_key = ?", (job.key,)
            ).fetchone()
            if row is not None:
                last_seen = datetime.fromisoformat(row[0])
                if last_seen > cutoff:
                    continue
            self._conn.execute(
                """
                INSERT INTO seen_jobs (job_key, title, company, url, source, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_key) DO UPDATE SET last_seen = excluded.last_seen
                """,
                (
                    job.key,
                    job.title,
                    job.company,
                    job.url,
                    job.source,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            fresh.append(job)

        self._conn.commit()
        return fresh

    def record_application(
        self,
        job: Job,
        score: float,
        reason: str,
        resume_path: str,
        ats_coverage: float,
    ) -> ApplicationRecord:
        prepared_at = _utcnow().isoformat()
        self._conn.execute(
            """
            INSERT INTO applications
                (job_key, title, company, url, score, reason, resume_path, ats_coverage, prepared_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.key,
                job.title,
                job.company,
                job.url,
                score,
                reason,
                resume_path,
                ats_coverage,
                prepared_at,
            ),
        )
        self._conn.commit()
        return ApplicationRecord(
            job_key=job.key,
            title=job.title,
            company=job.company,
            url=job.url,
            score=score,
            reason=reason,
            resume_path=resume_path,
            ats_coverage=ats_coverage,
            prepared_at=prepared_at,
        )

    def applications_since(self, hours: int = 24) -> List[ApplicationRecord]:
        cutoff = (_utcnow() - timedelta(hours=hours)).isoformat()
        rows = self._conn.execute(
            """
            SELECT job_key, title, company, url, score, reason, resume_path, ats_coverage, prepared_at
            FROM applications WHERE prepared_at >= ? ORDER BY score DESC
            """,
            (cutoff,),
        ).fetchall()
        return [ApplicationRecord(*row) for row in rows]

    # test helper: backdate a seen job so the >24h path can be exercised
    def _set_last_seen(self, job_key: str, when: datetime) -> None:
        self._conn.execute(
            "UPDATE seen_jobs SET last_seen = ? WHERE job_key = ?",
            (when.isoformat(), job_key),
        )
        self._conn.commit()
