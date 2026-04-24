# job_agent

Simple modular Python project:
- `scraper.py`: returns dummy job data
- `resume_parser.py`: parses plain-text resumes and extracts skills/contact data
- `scorer.py`: scores jobs with OpenAI API and falls back to local keyword scoring
- `main.py`: pipeline to parse resume text, score jobs, and print top matches

## Install
```bash
pip install -r requirements.txt
```

## Run
```bash
export OPENAI_API_KEY="your_key"  # optional; fallback works without it
python main.py --resume ./resume.txt --search python --top 3
```
