"""Pipeline entrypoint: scrape jobs, parse resume, score jobs, output top matches."""

from __future__ import annotations

import argparse
import sys

from resume_parser import parse_resume
from scraper import scrape_jobs
from scorer import score_jobs_with_openai


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value}")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Job matching pipeline")
    parser.add_argument("--resume", required=True, help="Path to plain-text resume file")
    parser.add_argument("--search", default="", help="Keyword to filter dummy jobs")
    parser.add_argument("--limit", type=positive_int, default=10, help="Max jobs to consider")
    parser.add_argument("--top", type=positive_int, default=3, help="Top N jobs to output")
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    try:
        profile = parse_resume(args.resume)
    except OSError as error:
        print(f"Error: could not read resume file '{args.resume}': {error}", file=sys.stderr)
        raise SystemExit(1)

    jobs = scrape_jobs(search=args.search, limit=args.limit)
    if not jobs:
        print(f"No jobs matched search keyword '{args.search}'.")
        return

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
