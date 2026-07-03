"""Job agent pipeline.

Commands:
    build-profile  Decipher your daily task/workload log into a resume profile.
    run            Daily run: scrape boards, dedupe (24h), score, prepare >=10
                   tailored ATS resumes, and write/email the morning digest.
    match          Legacy one-off matcher against a plain-text resume file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from config import Config, load_config
from digest import build_digest, build_digest_html, send_email_if_configured
from resume_builder import ats_check, build_profile, render_resume, tailor_profile
from resume_parser import parse_resume
from scorer import score_jobs_with_claude
from scraper import scrape_jobs
from sources import fetch_all
from store import JobStore


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value}")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Job matching and application agent")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    commands = parser.add_subparsers(dest="command", required=True)

    profile_cmd = commands.add_parser(
        "build-profile", help="Turn your daily task log into a resume profile"
    )
    profile_cmd.add_argument("--tasklog", help="Path to task/workload log (plain text)")

    run_cmd = commands.add_parser("run", help="Daily scrape/score/prepare/digest run")
    run_cmd.add_argument(
        "--offline", action="store_true", help="Use built-in dummy jobs (no network)"
    )

    match_cmd = commands.add_parser("match", help="Legacy resume-vs-dummy-jobs matcher")
    match_cmd.add_argument("--resume", required=True, help="Plain-text resume file")
    match_cmd.add_argument("--search", default="", help="Keyword filter")
    match_cmd.add_argument("--limit", type=positive_int, default=10)
    match_cmd.add_argument("--top", type=positive_int, default=3)
    match_cmd.add_argument("--model", default="claude-opus-4-8")

    return parser


def _slug(text: str, max_length: int = 60) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()[:max_length]


def cmd_build_profile(args: argparse.Namespace, config: Config) -> None:
    tasklog_path = Path(args.tasklog or config.tasklog_path)
    try:
        tasklog = tasklog_path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"Error: could not read task log '{tasklog_path}': {error}", file=sys.stderr)
        raise SystemExit(1)

    profile = build_profile(tasklog, model=config.model)
    Path(config.profile_path).write_text(
        json.dumps(profile, indent=2), encoding="utf-8"
    )
    resume = render_resume(profile)
    master_path = Path(config.profile_path).with_name("master_resume.txt")
    master_path.write_text(resume, encoding="utf-8")

    report = ats_check(resume)
    print(f"Profile written to {config.profile_path}")
    print(f"Master ATS resume written to {master_path}")
    print(f"Skills: {', '.join(profile.get('skills', [])) or 'none detected'}")
    if report["issues"]:
        print("ATS warnings:")
        for issue in report["issues"]:
            print(f"  - {issue}")


def cmd_run(args: argparse.Namespace, config: Config) -> None:
    profile_file = Path(config.profile_path)
    if not profile_file.exists():
        print(
            f"Error: no profile at '{config.profile_path}'. "
            "Run 'python main.py build-profile' first.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    profile = json.loads(profile_file.read_text(encoding="utf-8"))
    resume_text = render_resume(profile)

    if args.offline:
        jobs, errors = scrape_jobs(search="", limit=config.limit_per_source), {}
        print(f"Offline mode: using {len(jobs)} built-in dummy job(s)")
    else:
        jobs, errors = fetch_all(
            config.sources, config.keywords, config.location, config.limit_per_source
        )
        if not jobs:
            print("All job boards failed; falling back to offline dummy jobs.")
            jobs = scrape_jobs(search="", limit=config.limit_per_source)

        print(f"Fetched {len(jobs)} job(s) from {', '.join(config.sources)}")
        for source, error in errors.items():
            print(f"  warning: {source}: {error}")

    store = JobStore(config.db_path)
    try:
        fresh = store.filter_unseen(jobs, within_hours=config.dedupe_hours)
        print(f"{len(fresh)} new (not seen in the last {config.dedupe_hours}h)")

        ranked = score_jobs_with_claude(fresh, resume_text, model=config.model)
        suitable = [item for item in ranked if item.score >= config.score_threshold]
        selected = (
            suitable
            if len(suitable) >= config.min_jobs_per_day
            else ranked[: config.min_jobs_per_day]
        )
        selected = selected[: max(config.min_jobs_per_day, len(suitable))]

        today = date.today().isoformat()
        out_dir = Path(config.applications_dir) / today
        out_dir.mkdir(parents=True, exist_ok=True)

        for item in selected:
            tailored = tailor_profile(profile, item.job, model=config.model)
            resume = render_resume(tailored)
            report = ats_check(resume, item.job.description)
            resume_path = out_dir / f"{_slug(item.job.title)}--{_slug(item.job.company) or 'company'}.txt"
            resume_path.write_text(resume, encoding="utf-8")
            store.record_application(
                item.job, item.score, item.reason, str(resume_path), report["coverage"]
            )

        applications = store.applications_since(hours=24)
    finally:
        store.close()

    digest = build_digest(
        today, applications, source_errors=errors, min_jobs=config.min_jobs_per_day
    )
    digest_dir = Path(config.digest_dir)
    digest_dir.mkdir(parents=True, exist_ok=True)
    digest_path = digest_dir / f"{today}.md"
    digest_path.write_text(digest, encoding="utf-8")

    digest_html = build_digest_html(
        today, applications, source_errors=errors, min_jobs=config.min_jobs_per_day
    )
    (digest_dir / f"{today}.html").write_text(digest_html, encoding="utf-8")
    (digest_dir / "latest.html").write_text(digest_html, encoding="utf-8")

    sent = send_email_if_configured(f"Job digest {today}", digest)
    print(f"Prepared {len(selected)} application package(s) in {out_dir}")
    print(f"Digest written to {digest_path}" + (" and emailed" if sent else ""))


def cmd_match(args: argparse.Namespace) -> None:
    try:
        profile = parse_resume(args.resume)
    except OSError as error:
        print(f"Error: could not read resume file '{args.resume}': {error}", file=sys.stderr)
        raise SystemExit(1)

    jobs = scrape_jobs(search=args.search, limit=args.limit)
    if not jobs:
        print(f"No jobs matched search keyword '{args.search}'.")
        return

    ranked = score_jobs_with_claude(jobs=jobs, resume_text=profile.text, model=args.model)

    print(f"Parsed skills: {', '.join(profile.skills) or 'None detected'}")
    print(f"Top {min(args.top, len(ranked))} jobs:\n")
    for index, item in enumerate(ranked[: args.top], start=1):
        print(f"{index}. {item.job.title} @ {item.job.company}")
        print(f"   Score: {item.score:.1f}")
        print(f"   Reason: {item.reason}")
        print(f"   URL: {item.job.url}\n")


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)

    if args.command == "build-profile":
        cmd_build_profile(args, config)
    elif args.command == "run":
        cmd_run(args, config)
    elif args.command == "match":
        cmd_match(args)


if __name__ == "__main__":
    main()
