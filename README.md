# job_agent

Describe your daily tasks and workload in plain text — the agent deciphers it,
builds an ATS-friendly resume, scrapes jobs from **LinkedIn, Naukri, IIMJobs,
and Cutshort**, skips anything already seen in the last **24 hours**, prepares
tailored application packages for at least **10 suitable jobs a day**, and
sends you the list every morning.

Requires Python 3.10+.

## How it works

```
tasklog.txt ──build-profile──▶ profile.json + master_resume.txt (ATS format)
                                      │
job boards ──scrape──▶ dedupe (<24h seen? skip) ──score──▶ top ≥10 suitable
                                      │
                     tailored ATS resume per job + ATS lint
                                      │
                digests/YYYY-MM-DD.md  ──▶ emailed every morning (optional)
```

| Module | Role |
|---|---|
| `resume_builder.py` | task log → profile → ATS resume; per-job tailoring; ATS lint |
| `sources.py` | board adapters: `linkedin`, `naukri`, `iimjobs`, `cutshort` |
| `scraper.py` | LinkedIn guest scraping + `Job` model + offline dummy data |
| `store.py` | SQLite: 24h dedupe memory + application history |
| `scorer.py` | job-vs-resume scoring (OpenAI, offline keyword fallback) |
| `digest.py` | morning digest markdown + optional SMTP email |
| `main.py` | CLI: `build-profile`, `run`, legacy `match` |

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="your_key"   # optional; offline fallbacks work without it
```

1. Edit `tasklog.txt` — describe your daily tasks/workload in your own words.
2. Edit `config.json` — search keywords, location, boards, daily minimum.

## Use

```bash
python main.py build-profile          # tasklog.txt → profile.json + master_resume.txt
python main.py run                    # daily scrape → dedupe → score → prepare → digest
python main.py run --offline          # dry run with built-in dummy jobs
```

Each run writes tailored resumes to `applications/<date>/` and the morning
list to `digests/<date>.md`.

## Morning email (optional)

Set these environment variables and `run` will email the digest:
`SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USER`, `SMTP_PASSWORD`,
`DIGEST_TO`. For Gmail use an [app password](https://support.google.com/accounts/answer/185833).

## Run it every morning automatically

`.github/workflows/daily.yml` runs the pipeline daily at **08:00 IST**
(02:30 UTC — edit the cron for your morning). Add these repository secrets:
`OPENAI_API_KEY`, and optionally the `SMTP_*`/`DIGEST_TO` secrets for email.
The digest and application packages are also uploaded as a workflow artifact.

Or use plain cron on your own machine:

```cron
30 2 * * * cd /path/to/job_agent && python main.py run
```

## What "apply" means here (please read)

The agent prepares everything **up to** submission: per-job tailored,
ATS-linted resume + direct apply link, at least 10 per day. It does **not**
click "apply" for you — automated submission bots violate LinkedIn's (and most
boards') terms of service and commonly get accounts restricted. The morning
digest is designed so each application takes under a minute to submit.

Notes on the boards:
- **LinkedIn**: uses the public guest endpoints (no login). Be gentle; requests
  are rate-limited in code.
- **Naukri**: uses the public search API.
- **IIMJobs / Cutshort**: experimental — these sites render mostly client-side,
  so the HTML adapters may return sparse results and can need selector updates.

## Test

```bash
python -m unittest discover -s tests
```
