# job_agent

Describe your daily tasks and workload in plain text — the agent (powered by
**Claude / Anthropic API**) deciphers it, builds an ATS-friendly resume,
scrapes jobs from **LinkedIn, Naukri, IIMJobs, and Cutshort**, skips anything
already seen in the last **24 hours**, prepares tailored application packages
for at least **10 suitable jobs a day**, and publishes the list every morning
at a **URL** (GitHub Pages) and optionally by email.

Requires Python 3.10+.

## How it works

```
your details (TASKLOG secret) ──build-profile──▶ profile + master ATS resume
                                        │
job boards ──scrape──▶ dedupe (<24h seen? skip) ──score──▶ top ≥10 suitable
                                        │
                      tailored ATS resume per job + ATS lint
                                        │
        https://<user>.github.io/job_agent/latest.html  +  optional email
```

| Module | Role |
|---|---|
| `resume_builder.py` | task log → profile → ATS resume (Claude); per-job tailoring; ATS lint |
| `sources.py` | board adapters: `linkedin`, `naukri`, `iimjobs`, `cutshort` |
| `scraper.py` | LinkedIn guest scraping + `Job` model + offline dummy data |
| `store.py` | SQLite: 24h dedupe memory + application history |
| `scorer.py` | job-vs-resume scoring (Claude, offline keyword fallback) |
| `digest.py` | morning digest (markdown + HTML page) + optional SMTP email |
| `site/` | the public "tell it about yourself" setup page |
| `main.py` | CLI: `build-profile`, `run`, legacy `match` |

## Set up (one time)

Your personal details never go into the repository — they live in private
GitHub Actions secrets:

1. Open the setup page: `https://<your-username>.github.io/job_agent/`
   (published automatically by the daily workflow; run it once manually from
   the Actions tab to create the site). Fill in **everything about yourself**
   — daily tasks, projects, education, contact — and it generates your setup.
2. Add repository secrets (*Settings → Secrets and variables → Actions*):
   - `TASKLOG` — your personal task log (from the setup page)
   - `ANTHROPIC_API_KEY` — for resume building, tailoring, and scoring
     (offline fallbacks run without it, with lower quality)
   - Optional email: `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`,
     `SMTP_PASSWORD` (a Gmail [app password](https://support.google.com/accounts/answer/185833)),
     `DIGEST_TO`
3. Commit the generated `config.json` (keywords/location only — nothing personal).

The workflow runs daily at **08:00 IST** (edit the cron in
`.github/workflows/daily.yml`) and publishes the morning list at
`https://<your-username>.github.io/job_agent/latest.html`.
Tailored resumes (which contain your contact details) are **not** published to
the public site — they are uploaded as a private workflow artifact.

## Run locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your_key"   # optional; offline fallbacks work without it
# put your real details in tasklog.txt locally (it's only a template in the repo)
python main.py build-profile
python main.py run                    # or: python main.py run --offline (dry run)
```

Each run writes tailored resumes to `applications/<date>/` and the morning
list to `digests/<date>.md` + `.html`.

## What "apply" means here (please read)

The agent prepares everything **up to** submission: per-job tailored,
ATS-linted resume + direct apply link, at least 10 per day. It does **not**
click "apply" for you — automated submission bots violate LinkedIn's (and most
boards') terms of service and commonly get accounts restricted. The morning
digest is designed so each application takes under a minute to submit.

Notes on the boards:
- **LinkedIn**: public guest endpoints (no login), rate-limited in code.
- **Naukri**: public search API.
- **IIMJobs / Cutshort**: experimental — these sites render mostly client-side,
  so the HTML adapters may return sparse results and can need selector updates.

## Test

```bash
python -m unittest discover -s tests
```
