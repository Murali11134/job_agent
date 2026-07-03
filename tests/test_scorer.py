import unittest
from unittest import mock

from scorer import _extract_json, _fallback_score, score_jobs_with_claude
from scraper import Job

PYTHON_JOB = Job(
    title="Python Engineer",
    company="Acme",
    description="Build python services with docker and aws.",
    url="https://example.com/jobs/1",
)
UNRELATED_JOB = Job(
    title="Chef",
    company="Bistro",
    description="Cook seasonal menus.",
    url="https://example.com/jobs/2",
)


class ExtractJsonTests(unittest.TestCase):
    def test_parses_plain_json(self):
        self.assertEqual(
            _extract_json('{"score": 90, "reason": "good"}'),
            {"score": 90, "reason": "good"},
        )

    def test_parses_json_wrapped_in_markdown_fences(self):
        text = '```json\n{"score": 75, "reason": "ok"}\n```'
        self.assertEqual(_extract_json(text), {"score": 75, "reason": "ok"})

    def test_raises_when_no_json_present(self):
        with self.assertRaises(ValueError):
            _extract_json("no json here")


class FallbackScoreTests(unittest.TestCase):
    def test_overlapping_resume_scores_higher(self):
        resume = "Experienced python engineer using docker and aws."
        relevant = _fallback_score(PYTHON_JOB, resume)
        unrelated = _fallback_score(UNRELATED_JOB, resume)
        self.assertGreater(relevant.score, unrelated.score)

    def test_score_is_capped_at_100(self):
        resume = f"{PYTHON_JOB.title} {PYTHON_JOB.description} " * 10
        scored = _fallback_score(PYTHON_JOB, resume)
        self.assertLessEqual(scored.score, 100.0)


class ScoreJobsWithoutApiKeyTests(unittest.TestCase):
    @mock.patch.dict("os.environ", {}, clear=True)
    def test_falls_back_and_sorts_descending(self):
        resume = "Experienced python engineer using docker and aws."
        ranked = score_jobs_with_claude([UNRELATED_JOB, PYTHON_JOB], resume)
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0].job, PYTHON_JOB)
        self.assertGreaterEqual(ranked[0].score, ranked[1].score)


if __name__ == "__main__":
    unittest.main()
