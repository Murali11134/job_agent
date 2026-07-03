"""Morning digest: the daily list of prepared applications, emailed and/or published."""

from __future__ import annotations

import html
import os
import smtplib
from email.message import EmailMessage
from typing import Dict, List

from store import ApplicationRecord

HTML_STYLE = """
body { font-family: Georgia, serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem;
       color: #2b2b2b; background: #faf8f4; }
h1 { font-size: 1.5rem; } h2 { font-size: 1.1rem; margin-bottom: 0.2rem; }
.job { border: 1px solid #ddd; border-radius: 8px; padding: 0.8rem 1rem; margin: 0.8rem 0;
       background: #fff; }
.meta { color: #666; font-size: 0.9rem; }
.apply { display: inline-block; margin-top: 0.4rem; font-weight: bold; }
.warn { background: #fff6e0; border-left: 4px solid #d9a521; padding: 0.6rem 1rem; }
footer { color: #888; font-size: 0.85rem; margin-top: 2rem; }
"""


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


def build_digest_html(
    date_label: str,
    applications: List[ApplicationRecord],
    source_errors: Dict[str, str] | None = None,
    min_jobs: int = 10,
) -> str:
    """Render the morning digest as a self-contained HTML page (for GitHub Pages)."""

    esc = html.escape
    parts = [
        f"<style>{HTML_STYLE}</style>",
        f"<h1>Job applications prepared &mdash; {esc(date_label)}</h1>",
        f"<p>Prepared <strong>{len(applications)}</strong> application package(s) "
        f"(target: {min_jobs}/day).</p>",
    ]
    if len(applications) < min_jobs:
        parts.append(
            f'<p class="warn">Only {len(applications)} suitable new jobs found; '
            "consider broadening keywords or sources.</p>"
        )

    for index, app in enumerate(applications, start=1):
        company = f" @ {esc(app.company)}" if app.company else ""
        parts.append(
            '<div class="job">'
            f"<h2>{index}. {esc(app.title)}{company}</h2>"
            f'<div class="meta">Match {app.score:.0f}/100 &middot; '
            f"ATS coverage {app.ats_coverage:.0f}% &middot; {esc(app.reason)}</div>"
            f'<a class="apply" href="{esc(app.url)}">Apply &rarr;</a>'
            f'<div class="meta">Tailored resume: <code>{esc(app.resume_path)}</code> '
            "(workflow artifact)</div>"
            "</div>"
        )

    if source_errors:
        items = "".join(
            f"<li><code>{esc(source)}</code>: {esc(error)}</li>"
            for source, error in source_errors.items()
        )
        parts.append(f'<div class="warn"><strong>Source warnings</strong><ul>{items}</ul></div>')

    parts.append(
        "<footer>Resumes are tailored and ATS-linted. Review each package and "
        "submit via the apply link &mdash; submission is intentionally manual.</footer>"
    )
    return "\n".join(parts)


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
