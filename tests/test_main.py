import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from config import Config
from main import _resume_filename, cmd_run


class ResumeFilenameTests(unittest.TestCase):
    def test_same_title_and_company_get_unique_names_for_distinct_jobs(self):
        first = _resume_filename("Data Engineer", "", "iimjobs:1")
        second = _resume_filename("Data Engineer", "", "iimjobs:2")
        self.assertNotEqual(first, second)
        self.assertTrue(first.endswith(".txt"))


class CurrentRunDigestTests(unittest.TestCase):
    @mock.patch.dict("os.environ", {}, clear=True)
    def test_rerun_does_not_repeat_previous_applications(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_path = root / "profile.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "name": "Test User",
                        "email": "test@example.com",
                        "phone": "",
                        "title": "Engineer",
                        "summary": "Python engineer.",
                        "skills": ["python"],
                        "experience": [],
                        "education": [],
                    }
                ),
                encoding="utf-8",
            )
            config = Config(
                min_jobs_per_day=4,
                max_applications_per_run=4,
                profile_path=str(profile_path),
                db_path=str(root / "jobs.db"),
                applications_dir=str(root / "applications"),
                digest_dir=str(root / "digests"),
            )
            args = argparse.Namespace(offline=True)

            cmd_run(args, config)
            cmd_run(args, config)

            latest = (root / "digests" / "latest.html").read_text(encoding="utf-8")
            self.assertIn("Prepared <strong>0</strong>", latest)


if __name__ == "__main__":
    unittest.main()
