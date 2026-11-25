import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scraper import validate_public_data


class TestPublicDataValidation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.data_directory = self.root / "frontend" / "data"
        self.current_file = self.data_directory / "current.json"
        self.history_file = (
            self.data_directory / "history" / "2026" / "bisa.jsonl"
        )
        self.old_record = {
            "date": "2026-11-24",
            "captured_at": "2026-11-24T10:00:00-04:00",
            "id": "bisa",
            "name": "Banco BISA",
            "type": "commercial_bank",
            "buy": 11.0,
            "sell": 12.0,
        }
        self.new_record = {
            **self.old_record,
            "date": "2026-11-25",
            "captured_at": "2026-11-25T10:00:00-04:00",
        }
        self.current_file.parent.mkdir(parents=True)
        self.history_file.parent.mkdir(parents=True)
        self.current_file.write_text(
            json.dumps({"entities": [self.new_record]}), encoding="utf-8"
        )
        self.history_file.write_text(
            "\n".join(
                json.dumps(record)
                for record in (self.old_record, self.new_record)
            )
            + "\n",
            encoding="utf-8",
        )

        self.root_patch = patch.object(validate_public_data, "ROOT", self.root)
        self.data_patch = patch.object(
            validate_public_data, "DATA_DIRECTORY", self.data_directory
        )
        self.current_patch = patch.object(
            validate_public_data, "CURRENT_FILE", self.current_file
        )
        self.git_patch = patch.object(
            validate_public_data, "_git_output", side_effect=self.git_output
        )
        for active_patch in (
            self.root_patch,
            self.data_patch,
            self.current_patch,
            self.git_patch,
        ):
            active_patch.start()

    def tearDown(self):
        for active_patch in (
            self.git_patch,
            self.current_patch,
            self.data_patch,
            self.root_patch,
        ):
            active_patch.stop()
        self.temp_dir.cleanup()

    def git_output(self, *arguments):
        if arguments == ("show", "HEAD:frontend/data/current.json"):
            return json.dumps({"entities": [self.old_record]})
        if arguments == (
            "ls-tree",
            "-r",
            "--name-only",
            "HEAD",
            "--",
            "frontend/data/history",
        ):
            return "frontend/data/history/2026/bisa.jsonl\n"
        if arguments == ("show", "HEAD:frontend/data/history/2026/bisa.jsonl"):
            return json.dumps(self.old_record) + "\n"
        raise AssertionError(f"Unexpected git command: {arguments}")

    def test_accepts_valid_data_that_preserves_existing_history(self):
        validate_public_data.validate_public_data()

    def test_rejects_removed_historical_dates(self):
        self.history_file.write_text(
            json.dumps(self.new_record) + "\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(ValueError, "lost historical dates"):
            validate_public_data.validate_public_data()

    def test_rejects_invalid_current_rates(self):
        invalid_record = {**self.new_record, "buy": float("nan")}
        self.current_file.write_text(
            json.dumps({"entities": [invalid_record]}), encoding="utf-8"
        )

        with self.assertRaisesRegex(ValueError, "finite and positive"):
            validate_public_data.validate_public_data()


if __name__ == "__main__":
    unittest.main()
