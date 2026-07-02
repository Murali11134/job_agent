import unittest

from scraper import DUMMY_JOBS, scrape_jobs


class ScrapeJobsTests(unittest.TestCase):
    def test_returns_all_jobs_without_search(self):
        self.assertEqual(scrape_jobs(), DUMMY_JOBS)

    def test_search_filters_by_keyword(self):
        jobs = scrape_jobs(search="python")
        self.assertTrue(jobs)
        for job in jobs:
            haystack = f"{job.title} {job.description} {job.company}".lower()
            self.assertIn("python", haystack)

    def test_search_is_case_insensitive(self):
        self.assertEqual(scrape_jobs(search="PYTHON"), scrape_jobs(search="python"))

    def test_search_with_no_matches_returns_empty(self):
        self.assertEqual(scrape_jobs(search="zzz-no-such-keyword"), [])

    def test_limit_truncates_results(self):
        self.assertEqual(len(scrape_jobs(limit=2)), 2)

    def test_zero_or_negative_limit_returns_empty(self):
        self.assertEqual(scrape_jobs(limit=0), [])
        self.assertEqual(scrape_jobs(limit=-3), [])


if __name__ == "__main__":
    unittest.main()
