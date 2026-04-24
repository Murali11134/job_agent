"""Pipeline entrypoint: scrape jobs, parse resume, score jobs, output top matches."""

from __future__ import annotations

import argparse

from resume_parser import parse_resume
from scraper import scrape_jobs
from scorer import score_jobs_with_openai


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Job matching pipeline")
    parser.add_argument("--resume", required=True, help="Path to plain-text resume file")
    parser.add_argument("--search", default="", help="Keyword to filter dummy jobs")
    parser.add_argument("--limit", type=int, default=10, help="Max jobs to consider")
    parser.add_argument("--top", type=int, default=3, help="Top N jobs to output")
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    profile = parse_resume(args.resume)
    jobs = scrape_jobs(search=args.search, limit=args.limit)
    ranked = score_jobs_with_openai(jobs=jobs, resume_text=profile.text, model=args.model)

    print(f"Parsed skills: {', '.join(profile.skills) or 'None detected'}")
    print(f"Top {min(args.top, len(ranked))} jobs:\n")
    for index, item in enumerate(ranked[: args.top], start=1):
        print(f"{index}. {item.job.title} @ {item.job.company}")
        print(f"   Score: {item.score:.1f}")
        print(f"   Reason: {item.reason}")
        print(f"   URL: {item.job.url}\n")


if __name__ == "__main__":
    main()
