import unittest

from scraper import parse_job_description, parse_search_results
from sources import (
    fetch_all,
    parse_cutshort_results,
    parse_iimjobs_results,
    parse_naukri_results,
)

LINKEDIN_HTML = """
<ul>
  <li>
    <div class="base-card" data-entity-urn="urn:li:jobPosting:4001">
      <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/python-developer-4001?refId=x">
        Python Developer
      </a>
      <h3 class="base-search-card__title">Python Developer</h3>
      <h4 class="base-search-card__subtitle"><a>Acme Corp</a></h4>
      <span class="job-search-card__location">Bengaluru, India</span>
      <time datetime="2026-07-01">1 day ago</time>
    </div>
  </li>
  <li><div class="not-a-job">advert</div></li>
</ul>
"""

LINKEDIN_POSTING_HTML = """
<section class="description">
  <div class="show-more-less-html__markup">
    <p>Build APIs with <strong>FastAPI</strong>.</p><ul><li>Use Docker</li></ul>
  </div>
</section>
"""

NAUKRI_PAYLOAD = {
    "jobDetails": [
        {
            "title": "Backend Engineer",
            "companyName": "Widgets Ltd",
            "jobDescription": "Python, Django, AWS",
            "jdURL": "/job-listings-backend-123",
            "jobId": "123",
            "placeholders": [{"type": "location", "label": "Hyderabad"}],
            "footerPlaceholderLabel": "2 Days Ago",
        }
    ]
}

IIMJOBS_HTML = """
<div>
  <a href="/j/senior-python-engineer-fintech-999888">Senior Python Engineer - Fintech</a>
  <a href="/j/senior-python-engineer-fintech-999888">Senior Python Engineer - Fintech</a>
  <a href="/about">About us</a>
</div>
"""

CUTSHORT_HTML = """
<div>
  <a href="/job/python-developer-acme-xyz1">Python Developer at Acme</a>
  <a href="/companies/acme">Acme</a>
</div>
"""


class LinkedInParserTests(unittest.TestCase):
    def test_parses_job_cards(self):
        jobs = parse_search_results(LINKEDIN_HTML)
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Python Developer")
        self.assertEqual(job.company, "Acme Corp")
        self.assertEqual(job.job_id, "4001")
        self.assertEqual(job.location, "Bengaluru, India")
        self.assertEqual(job.source, "linkedin")
        self.assertNotIn("?", job.url)

    def test_parses_posting_description(self):
        text = parse_job_description(LINKEDIN_POSTING_HTML)
        self.assertIn("FastAPI", text)
        self.assertIn("Use Docker", text)


class NaukriParserTests(unittest.TestCase):
    def test_parses_api_payload(self):
        jobs = parse_naukri_results(NAUKRI_PAYLOAD)
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Backend Engineer")
        self.assertEqual(job.company, "Widgets Ltd")
        self.assertEqual(job.url, "https://www.naukri.com/job-listings-backend-123")
        self.assertEqual(job.location, "Hyderabad")
        self.assertEqual(job.key, "naukri:123")


class BestEffortParserTests(unittest.TestCase):
    def test_iimjobs_dedupes_links_and_skips_non_jobs(self):
        jobs = parse_iimjobs_results(IIMJOBS_HTML)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].job_id, "999888")
        self.assertEqual(jobs[0].source, "iimjobs")

    def test_cutshort_extracts_job_links_only(self):
        jobs = parse_cutshort_results(CUTSHORT_HTML)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].url, "https://cutshort.io/job/python-developer-acme-xyz1")
        self.assertEqual(jobs[0].source, "cutshort")


class FetchAllTests(unittest.TestCase):
    def test_board_failures_are_collected_not_raised(self):
        jobs, errors = fetch_all(["nope"], "python", "India", 5)
        self.assertEqual(jobs, [])
        self.assertIn("nope", errors)

    def test_cross_board_duplicates_collapse(self):
        from scraper import Job
        import sources

        def board_a(keywords, location, limit):
            return [Job("Dev", "Acme", "d", "u1", job_id="1", source="a")]

        def board_b(keywords, location, limit):
            return [
                Job("Dev", "Acme", "d", "u2", job_id="2", source="b"),
                Job("Other", "Beta", "d", "u3", job_id="3", source="b"),
            ]

        original = dict(sources.SOURCES)
        sources.SOURCES.update({"a": board_a, "b": board_b})
        try:
            jobs, errors = fetch_all(["a", "b"], "x", "y", 5)
        finally:
            sources.SOURCES.clear()
            sources.SOURCES.update(original)

        self.assertEqual(errors, {})
        self.assertEqual([job.title for job in jobs], ["Dev", "Other"])


if __name__ == "__main__":
    unittest.main()
