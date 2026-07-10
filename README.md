# job_agent

Describe your daily tasks and workload in plain text — the agent (powered by
**Claude / Anthropic API**) deciphers it, builds an ATS-friendly resume,
scrapes jobs from **LinkedIn, Naukri, IIMJobs, and Cutshort**, skips anything
already seen in the last **24 hours**, prepares tailored application packages
for up to **10 suitable jobs a day**, and optionally delivers the list by email,
an encrypted workflow artifact, or an explicitly enabled public GitHub Pages URL.

Requires Python 3.10+.

## How it works

```
your details (TASKLOG secret) ──build-profile──▶ profile + master ATS resume
                                        │
job boards ──scrape──▶ dedupe (<24h seen? skip) ──score──▶ top ≥10 suitable
                                        │
                      tailored ATS resume per job + ATS lint
                                        │
      optional email / encrypted archive / explicitly public GitHub Pages
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

Your personal details never go into the repository — they live in GitHub
Actions secrets. Generated resumes are never uploaded in plaintext:

1. Prepare a plain-text task log containing **everything about yourself** —
   daily tasks, projects, education, and contact details. You can generate it
   locally with `site/index.html`. If you deliberately enabled public Pages,
   the same browser-only generator is available at
   `https://<your-username>.github.io/job_agent/`; it sends nothing anywhere.
2. Add repository secrets (*Settings → Secrets and variables → Actions*):
   - `TASKLOG` — your personal task log (from the setup page)
   - `ANTHROPIC_API_KEY` — for resume building, tailoring, and scoring
     (offline fallbacks run without it, with lower quality)
   - Optional encrypted download: `RESUME_ARCHIVE_PASSWORD` — use a strong,
     unique password. The workflow encrypts resumes and digests with AES-256 and
     PBKDF2 key derivation, then keeps the encrypted artifact for seven days.
   - Optional email: `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`,
     `SMTP_PASSWORD` (a Gmail [app password](https://support.google.com/accounts/answer/185833)),
     `DIGEST_TO`
3. Commit the generated `config.json` (keywords/location only — nothing personal).
4. Optional public page: create a repository **variable** named
   `PUBLISH_DIGEST` with value `true`. This deliberately makes job titles,
   companies, scores, and apply links public. Leave it unset for private use.

The workflow runs daily at **08:00 IST** (edit the cron in
`.github/workflows/daily.yml`). If public publishing is enabled, the morning list
appears at `https://<your-username>.github.io/job_agent/latest.html`.
Tailored resumes contain contact details and are never published or uploaded in
plaintext. When `RESUME_ARCHIVE_PASSWORD` is configured, they are included only
inside the encrypted seven-day artifact.

Decrypt a downloaded artifact with OpenSSL, then extract it:

```bash
export RESUME_ARCHIVE_PASSWORD='your-strong-password'
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -pass env:RESUME_ARCHIVE_PASSWORD \
  -in private-daily-output.tar.gz.enc -out private-daily-output.tar.gz
tar -xzf private-daily-output.tar.gz
```

## Run locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your_key"   # optional; offline fallbacks work without it
# put your real details in tasklog.txt locally (it's only a template in the repo)
python main.py build-profile
python main.py run                    # or: python main.py run --offline (dry run)
```

Each run writes tailored resumes to `applications/<date>/` and the morning
list to `digests/<date>.md` + `.html`. Claude output may reorder existing skills,
but the code rejects invented or renamed skills.

## What "apply" means here (please read)

The agent prepares everything **up to** submission: per-job tailored,
ATS-linted resume + direct apply link, up to the configured daily maximum. It does **not**
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
