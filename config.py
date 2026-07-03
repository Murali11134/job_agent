"""Pipeline configuration loaded from config.json with sensible defaults."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


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
    model: str = "claude-opus-4-8"
    tasklog_path: str = "tasklog.txt"
    profile_path: str = "profile.json"
    db_path: str = "job_agent.db"
    applications_dir: str = "applications"
    digest_dir: str = "digests"


def load_config(path: str = "config.json") -> Config:
    config = Config()
    file = Path(path)
    if file.exists():
        data = json.loads(file.read_text(encoding="utf-8"))
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
    return config
