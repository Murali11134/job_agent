"""Pipeline configuration loaded from config.json with sensible defaults."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


VALID_SOURCES = {"linkedin", "naukri", "iimjobs", "cutshort"}


@dataclass
class Config:
    keywords: str = "python developer"
    location: str = "India"
    sources: List[str] = field(
        default_factory=lambda: ["linkedin", "naukri", "iimjobs", "cutshort"]
    )
    min_jobs_per_day: int = 10
    limit_per_source: int = 25
    score_threshold: float = 35.0
    dedupe_hours: int = 24
    max_jobs_to_score: int = 50
    max_applications_per_run: int = 10
    model: str = "claude-opus-4-8"
    tasklog_path: str = "tasklog.txt"
    profile_path: str = "profile.json"
    db_path: str = "job_agent.db"
    applications_dir: str = "applications"
    digest_dir: str = "digests"

    def validate(self) -> None:
        if not isinstance(self.keywords, str) or not self.keywords.strip():
            raise ValueError("'keywords' must be a non-empty string")
        if not isinstance(self.location, str) or not self.location.strip():
            raise ValueError("'location' must be a non-empty string")
        if not isinstance(self.sources, list) or not self.sources:
            raise ValueError("'sources' must be a non-empty list")
        if any(
            not isinstance(source, str) or source not in VALID_SOURCES
            for source in self.sources
        ):
            raise ValueError(
                "'sources' may only contain: " + ", ".join(sorted(VALID_SOURCES))
            )
        if len(self.sources) != len(set(self.sources)):
            raise ValueError("'sources' must not contain duplicates")

        for name in (
            "min_jobs_per_day",
            "limit_per_source",
            "dedupe_hours",
            "max_jobs_to_score",
            "max_applications_per_run",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"'{name}' must be a positive integer")
        if self.max_applications_per_run < self.min_jobs_per_day:
            raise ValueError(
                "'max_applications_per_run' must be at least 'min_jobs_per_day'"
            )
        if isinstance(self.score_threshold, bool) or not isinstance(
            self.score_threshold, (int, float)
        ):
            raise ValueError("'score_threshold' must be a number from 0 to 100")
        if not 0 <= float(self.score_threshold) <= 100:
            raise ValueError("'score_threshold' must be between 0 and 100")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("'model' must be a non-empty string")
        for name in (
            "tasklog_path",
            "profile_path",
            "db_path",
            "applications_dir",
            "digest_dir",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"'{name}' must be a non-empty path string")


def load_config(path: str = "config.json") -> Config:
    config = Config()
    file = Path(path)
    if file.exists():
        data = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("configuration must be a JSON object")
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(f"unknown configuration option: '{key}'")
    config.validate()
    return config
