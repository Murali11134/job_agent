import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scraper import Job
from store import JobStore

JOB = Job(
    title="Python Engineer",
    company="Acme",
    description="python",
    url="https://example.com/jobs/1",
    job_id="111",
    source="linkedin",
)


class JobStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.store = JobStore(str(Path(self._tmpdir.name) / "test.db"))
        self.addCleanup(self.store.close)

    def test_first_sighting_passes_through(self):
        self.assertEqual(self.store.filter_unseen([JOB]), [JOB])

    def test_repeat_within_24h_is_dropped(self):
        self.store.filter_unseen([JOB])
        self.assertEqual(self.store.filter_unseen([JOB]), [])

    def test_repeat_after_24h_passes_again(self):
        self.store.filter_unseen([JOB])
        stale = datetime.now(timezone.utc) - timedelta(hours=25)
        self.store._set_last_seen(JOB.key, stale)
        self.assertEqual(self.store.filter_unseen([JOB]), [JOB])

    def test_dedup_key_prefers_source_and_job_id(self):
        self.assertEqual(JOB.key, "linkedin:111")
        dummy = Job(title="T", company="C", description="", url="u")
        self.assertEqual(dummy.key, "t|c")

    def test_applications_recorded_and_listed(self):
        self.store.record_application(JOB, 88.0, "great fit", "applications/x.txt", 75.0)
        apps = self.store.applications_since(hours=24)
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].title, "Python Engineer")
        self.assertEqual(apps[0].ats_coverage, 75.0)


if __name__ == "__main__":
    unittest.main()
