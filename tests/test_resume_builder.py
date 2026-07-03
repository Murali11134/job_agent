import unittest
from unittest import mock

from resume_builder import (
    ats_check,
    build_profile,
    job_keywords,
    render_resume,
    tailor_profile,
)
from scraper import Job

TASKLOG = """\
Jane Doe
jane.doe@example.com

- Built and maintained Python backend services with FastAPI and PostgreSQL
- Deployed services with Docker on AWS and fixed production issues
- Analyzed product data with pandas and SQL
"""


@mock.patch.dict("os.environ", {}, clear=True)
class OfflineProfileTests(unittest.TestCase):
    def test_build_profile_extracts_contacts_and_skills(self):
        profile = build_profile(TASKLOG)
        self.assertEqual(profile["email"], "jane.doe@example.com")
        self.assertEqual(profile["name"], "Jane Doe")
        for skill in ("python", "fastapi", "docker", "aws", "pandas", "sql"):
            self.assertIn(skill, profile["skills"])

    def test_render_resume_has_ats_sections_and_contact(self):
        resume = render_resume(build_profile(TASKLOG))
        for section in ("SUMMARY", "SKILLS", "EXPERIENCE", "EDUCATION"):
            self.assertIn(section, resume)
        self.assertIn("jane.doe@example.com", resume)
        self.assertNotIn("\t", resume)

    def test_tailor_profile_floats_matching_skills_first(self):
        profile = build_profile(TASKLOG)
        job = Job(
            title="Data Analyst",
            company="Insight",
            description="Analyze data with pandas and sql dashboards.",
            url="https://example.com/j/1",
        )
        tailored = tailor_profile(profile, job)
        top_two = set(tailored["skills"][:2])
        self.assertTrue(top_two & {"pandas", "sql"})
        self.assertEqual(sorted(tailored["skills"]), sorted(profile["skills"]))


class AtsCheckTests(unittest.TestCase):
    def test_full_coverage_when_keywords_present(self):
        resume = "SUMMARY\npython dev a@b.com\nSKILLS\npython\nEXPERIENCE\nEDUCATION"
        report = ats_check(resume, "python python python")
        self.assertEqual(report["coverage"], 100.0)
        self.assertEqual(report["missing_keywords"], [])

    def test_missing_keywords_lower_coverage(self):
        resume = "SUMMARY\na@b.com\nSKILLS\npython\nEXPERIENCE\nEDUCATION"
        report = ats_check(resume, "kubernetes kubernetes terraform terraform")
        self.assertLess(report["coverage"], 100.0)
        self.assertIn("kubernetes", report["missing_keywords"])

    def test_flags_missing_sections_and_email(self):
        report = ats_check("just some text")
        issues = " ".join(report["issues"])
        self.assertIn("SUMMARY", issues)
        self.assertIn("email", issues.lower())

    def test_job_keywords_filters_stopwords(self):
        keywords = job_keywords("We are looking for python and aws experience")
        self.assertIn("python", keywords)
        self.assertNotIn("and", keywords)
        self.assertNotIn("experience", keywords)


if __name__ == "__main__":
    unittest.main()
