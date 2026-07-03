import unittest
from unittest import mock

from digest import build_digest, build_digest_html, send_email_if_configured
from store import ApplicationRecord


def _record(title="Python Engineer", score=80.0):
    return ApplicationRecord(
        job_key="linkedin:1",
        title=title,
        company="Acme",
        url="https://example.com/jobs/1",
        score=score,
        reason="Strong skill match",
        resume_path="applications/2026-07-02/python-engineer--acme.txt",
        ats_coverage=72.0,
        prepared_at="2026-07-02T03:00:00+00:00",
    )


class BuildDigestTests(unittest.TestCase):
    def test_lists_jobs_with_links_and_scores(self):
        digest = build_digest("2026-07-02", [_record()], min_jobs=10)
        self.assertIn("Python Engineer", digest)
        self.assertIn("https://example.com/jobs/1", digest)
        self.assertIn("80/100", digest)
        self.assertIn("72%", digest)

    def test_warns_when_below_daily_target(self):
        digest = build_digest("2026-07-02", [_record()], min_jobs=10)
        self.assertIn("Only 1 suitable new jobs", digest)

    def test_no_warning_at_target(self):
        records = [_record(title=f"Job {i}") for i in range(10)]
        digest = build_digest("2026-07-02", records, min_jobs=10)
        self.assertNotIn("Only", digest)

    def test_includes_source_warnings(self):
        digest = build_digest(
            "2026-07-02", [_record()], source_errors={"naukri": "timeout"}
        )
        self.assertIn("naukri", digest)
        self.assertIn("timeout", digest)


class BuildDigestHtmlTests(unittest.TestCase):
    def test_contains_job_link_and_scores(self):
        page = build_digest_html("2026-07-02", [_record()], min_jobs=10)
        self.assertIn("Python Engineer", page)
        self.assertIn('href="https://example.com/jobs/1"', page)
        self.assertIn("80/100", page)

    def test_escapes_html_in_job_fields(self):
        record = _record(title="<script>alert(1)</script>")
        page = build_digest_html("2026-07-02", [record], min_jobs=1)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_includes_source_warnings(self):
        page = build_digest_html(
            "2026-07-02", [_record()], source_errors={"naukri": "timeout"}
        )
        self.assertIn("naukri", page)
        self.assertIn("timeout", page)


class SendEmailTests(unittest.TestCase):
    @mock.patch.dict("os.environ", {}, clear=True)
    def test_returns_false_without_smtp_config(self):
        self.assertFalse(send_email_if_configured("subject", "body"))

    @mock.patch.dict(
        "os.environ",
        {
            "SMTP_HOST": "smtp.test",
            "SMTP_USER": "u@test",
            "SMTP_PASSWORD": "pw",
            "DIGEST_TO": "me@test",
        },
        clear=True,
    )
    @mock.patch("digest.smtplib.SMTP")
    def test_sends_when_configured(self, smtp_cls):
        self.assertTrue(send_email_if_configured("subject", "body"))
        smtp = smtp_cls.return_value.__enter__.return_value
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("u@test", "pw")
        smtp.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
