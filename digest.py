"""Morning digest: the daily list of prepared applications, optionally emailed."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Dict, List

from store import ApplicationRecord


def build_digest(
    date_label: str,
    applications: List[ApplicationRecord],
    source_errors: Dict[str, str] | None = None,
    min_jobs: int = 10,
) -> str:
    """Render the morning digest as markdown."""

    lines = [
        f"# Job applications prepared - {date_label}",
        "",
        f"Prepared **{len(applications)}** application package(s) "
        f"(target: {min_jobs}/day).",
        "",
    ]
    if len(applications) < min_jobs:
        lines.append(
            f"> Only {len(applications)} suitable new jobs found in the last run; "
            "consider broadening keywords or sources."
        )
        lines.append("")

    for index, app in enumerate(applications, start=1):
        lines.extend(
            [
                f"## {index}. {app.title}" + (f" @ {app.company}" if app.company else ""),
                f"- Match score: {app.score:.0f}/100",
                f"- ATS keyword coverage: {app.ats_coverage:.0f}%",
                f"- Why: {app.reason}",
                f"- Apply: {app.url}",
                f"- Tailored resume: `{app.resume_path}`",
                "",
            ]
        )

    if source_errors:
        lines.append("## Source warnings")
        for source, error in source_errors.items():
            lines.append(f"- `{source}`: {error}")
        lines.append("")

    lines.append(
        "_Resumes are tailored and ATS-linted. Review each package and submit "
        "via the apply link - submission is intentionally manual._"
    )
    return "\n".join(lines)


def send_email_if_configured(subject: str, body_markdown: str) -> bool:
    """Email the digest when SMTP_* env vars are set. Returns True if sent.

    Required env: SMTP_HOST, SMTP_USER, SMTP_PASSWORD, DIGEST_TO.
    Optional: SMTP_PORT (default 587).
    """

    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    to_address = os.getenv("DIGEST_TO")
    if not all((host, user, password, to_address)):
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = user
    message["To"] = to_address
    message.set_content(body_markdown)

    port = int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(message)
    return True
