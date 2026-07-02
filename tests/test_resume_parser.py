import tempfile
import unittest
from pathlib import Path

from resume_parser import parse_resume

SAMPLE_RESUME = """\
Jane Doe
jane.doe@example.com
+1 555-123-4567

Backend engineer with Python, SQL, Docker, and AWS experience.
Built machine learning pipelines with pandas.
"""


class ParseResumeTests(unittest.TestCase):
    def _write_resume(self, text: str) -> str:
        path = Path(self._tmpdir.name) / "resume.txt"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def test_extracts_email_and_phone(self):
        profile = parse_resume(self._write_resume(SAMPLE_RESUME))
        self.assertEqual(profile.email, "jane.doe@example.com")
        self.assertIsNotNone(profile.phone)
        self.assertIn("555-123-4567", profile.phone)

    def test_extracts_known_skills_sorted(self):
        profile = parse_resume(self._write_resume(SAMPLE_RESUME))
        self.assertEqual(
            profile.skills,
            ["aws", "docker", "machine learning", "pandas", "python", "sql"],
        )

    def test_handles_resume_without_contact_info(self):
        profile = parse_resume(self._write_resume("Just some text with no contacts."))
        self.assertIsNone(profile.email)
        self.assertIsNone(profile.phone)
        self.assertEqual(profile.skills, [])

    def test_missing_file_raises_oserror(self):
        with self.assertRaises(OSError):
            parse_resume(str(Path(self._tmpdir.name) / "does-not-exist.txt"))


if __name__ == "__main__":
    unittest.main()
