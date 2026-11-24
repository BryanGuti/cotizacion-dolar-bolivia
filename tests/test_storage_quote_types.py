
import json
import tempfile
import unittest

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from scraper.utils.storage import save_quote


class TestStorageQuotationTypes(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.current_file = self.temp_path / "current.json"
        self.history_dir = self.temp_path / "history"

        self.current_patch = patch(
            "scraper.utils.storage.CURRENT_DATA_FILE",
            self.current_file,
        )

        self.history_patch = patch(
            "scraper.utils.storage.HISTORY_DIR",
            self.history_dir,
        )

        self.current_patch.start()
        self.history_patch.start()

    def tearDown(self):
        self.current_patch.stop()
        self.history_patch.stop()
        self.temp_dir.cleanup()

    def read_current(self):
        with self.current_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def read_history(self):
        history_file = self.history_dir / "2026.jsonl"

        with history_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            return [
                json.loads(line)
                for line in file
                if line.strip()
            ]

    def make_bcb_quote(
        self,
        date="2026-11-23",
        rate="11.75",
    ):
        return {
            "date": date,
            "captured_at": f"{date}T08:00:00-04:00",
            "official_rate": Decimal(rate),
        }

    def make_bisa_quote(
        self,
        date="2026-11-23",
        buy="6.85",
        sell="6.96",
    ):
        return {
            "date": date,
            "captured_at": f"{date}T08:30:00-04:00",
            "buy": Decimal(buy),
            "sell": Decimal(sell),
        }

    def test_saves_central_bank_official_rate(self):
        entity = {
            "id": "bcb",
            "name": "Banco Central de Bolivia",
            "type": "central_bank",
        }

        save_quote(entity, self.make_bcb_quote())

        current = self.read_current()
        history = self.read_history()

        record = current["entities"][0]

        self.assertEqual(record["official_rate"], 11.75)
        self.assertNotIn("buy", record)
        self.assertNotIn("sell", record)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["official_rate"], 11.75)

    def test_saves_commercial_bank_buy_and_sell(self):
        entity = {
            "id": "bisa",
            "name": "Banco BISA",
            "type": "commercial_bank",
        }

        save_quote(entity, self.make_bisa_quote())

        current = self.read_current()
        history = self.read_history()

        record = current["entities"][0]

        self.assertEqual(record["buy"], 6.85)
        self.assertEqual(record["sell"], 6.96)
        self.assertNotIn("official_rate", record)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["buy"], 6.85)
        self.assertEqual(history[0]["sell"], 6.96)

    def test_bcb_and_commercial_bank_are_stored_independently(self):
        bcb = {
            "id": "bcb",
            "name": "Banco Central de Bolivia",
            "type": "central_bank",
        }

        bisa = {
            "id": "bisa",
            "name": "Banco BISA",
            "type": "commercial_bank",
        }

        save_quote(bcb, self.make_bcb_quote())
        save_quote(bisa, self.make_bisa_quote())

        current = self.read_current()
        history = self.read_history()

        records = {
            record["id"]: record
            for record in current["entities"]
        }

        self.assertEqual(
            records["bcb"]["official_rate"],
            11.75,
        )

        self.assertEqual(records["bisa"]["buy"], 6.85)
        self.assertEqual(records["bisa"]["sell"], 6.96)

        self.assertEqual(len(history), 2)

    def test_older_bcb_quote_does_not_replace_current_rate(self):
        entity = {
            "id": "bcb",
            "name": "Banco Central de Bolivia",
            "type": "central_bank",
        }

        latest_quote = self.make_bcb_quote(
            date="2026-11-23",
            rate="11.75",
        )

        older_quote = self.make_bcb_quote(
            date="2026-11-20",
            rate="11.50",
        )

        save_quote(entity, latest_quote)
        save_quote(entity, older_quote)

        current = self.read_current()
        history = self.read_history()

        self.assertEqual(len(current["entities"]), 1)

        self.assertEqual(
            current["entities"][0]["date"],
            "2026-11-23",
        )

        self.assertEqual(
            current["entities"][0]["official_rate"],
            11.75,
        )

        self.assertEqual(len(history), 2)


if __name__ == "__main__":
    unittest.main()
