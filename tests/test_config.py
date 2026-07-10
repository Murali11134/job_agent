import json
import tempfile
import unittest
from pathlib import Path

from config import Config, load_config


class ConfigValidationTests(unittest.TestCase):
    def _load(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return load_config(str(path))

    def test_defaults_are_valid(self):
        Config().validate()

    def test_rejects_unknown_option(self):
        with self.assertRaisesRegex(ValueError, "unknown configuration option"):
            self._load({"surprise": True})

    def test_rejects_invalid_source(self):
        with self.assertRaisesRegex(ValueError, "sources"):
            self._load({"sources": ["linkedin", "unknown"]})

    def test_rejects_invalid_threshold(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 100"):
            self._load({"score_threshold": 101})

    def test_daily_cap_must_cover_target(self):
        with self.assertRaisesRegex(ValueError, "at least"):
            self._load({"min_jobs_per_day": 10, "max_applications_per_run": 5})


if __name__ == "__main__":
    unittest.main()
