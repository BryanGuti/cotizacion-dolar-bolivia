
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scraper.utils.progress import (
    load_progress,
    is_entity_completed,
    update_entity_status,
)


class TestProgress(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.progress_file = Path(self.temp_dir.name) / "progress.json"

        self.progress_patch = patch(
            "scraper.utils.progress.PROGRESS_FILE",
            self.progress_file,
        )
        self.progress_patch.start()

        self.today = "2026-11-23"

    def tearDown(self):
        self.progress_patch.stop()
        self.temp_dir.cleanup()

    def test_creates_new_progress_file(self):
        progress = load_progress(self.today)

        self.assertEqual(progress["date"], self.today)
        self.assertEqual(progress["entities"], {})
        self.assertTrue(self.progress_file.exists())

    def test_successful_entity_is_marked_as_completed(self):
        progress = load_progress(self.today)

        update_entity_status(progress, "bisa", "success")

        self.assertTrue(
            is_entity_completed(progress, "bisa")
        )

        # Verify that the status was persisted.
        saved_progress = load_progress(self.today)

        self.assertTrue(
            is_entity_completed(saved_progress, "bisa")
        )

    def test_failed_entity_can_be_retried(self):
        progress = load_progress(self.today)

        update_entity_status(progress, "bcp", "failed")

        self.assertFalse(
            is_entity_completed(progress, "bcp")
        )

    def test_progress_resets_when_date_changes(self):
        progress = load_progress(self.today)
        update_entity_status(progress, "bisa", "success")

        next_day = "2026-11-24"
        new_progress = load_progress(next_day)

        self.assertEqual(new_progress["date"], next_day)
        self.assertEqual(new_progress["entities"], {})

    def test_invalid_progress_file_is_reset(self):
        self.progress_file.write_text(
            "{ invalid json",
            encoding="utf-8",
        )

        progress = load_progress(self.today)

        self.assertEqual(progress["date"], self.today)
        self.assertEqual(progress["entities"], {})

        # The file should now contain valid JSON.
        with self.progress_file.open("r", encoding="utf-8") as file:
            saved_progress = json.load(file)

        self.assertEqual(saved_progress["date"], self.today)


if __name__ == "__main__":
    unittest.main()
