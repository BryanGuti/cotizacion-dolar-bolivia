
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from scraper.utils.storage import (
    get_current_record,
    get_history_record,
    repair_quote_storage,
    save_quote,
)


class TestStorage(unittest.TestCase):

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

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def make_entity(self, entity_id="bisa", name="Banco BISA"):
        return {
            "id": entity_id,
            "name": name,
            "type": "commercial_bank",
        }

    def make_quote(
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

    def make_bcb_quote(
        self,
        date="2026-11-24",
        rate="11.75",
    ):
        return {
            "date": date,
            "captured_at": f"{date}T08:00:00-04:00",
            "official_rate": Decimal(rate),
        }

    def make_bisa_quote(
        self,
        date="2026-11-24",
        buy="6.85",
        sell="6.96",
    ):
        return {
            "date": date,
            "captured_at": f"{date}T08:30:00-04:00",
            "buy": Decimal(buy),
            "sell": Decimal(sell),
        }

    def read_current(self):
        with self.current_file.open("r", encoding="utf-8") as file:
            return json.load(file)

    def read_current_records(self):
        return self.read_current()["entities"]

    def read_history(self, entity_id="bisa", year="2026"):
        history_file = self.history_dir / year / f"{entity_id}.jsonl"

        if not history_file.exists():
            return []

        with history_file.open("r", encoding="utf-8") as file:
            return [
                json.loads(line)
                for line in file
                if line.strip()
            ]

    # ---------------------------------------------------------
    # Current and historical storage
    # ---------------------------------------------------------

    def test_saves_new_quote(self):
        entity = self.make_entity()
        quote = self.make_quote()

        save_quote(entity, quote)

        current = self.read_current_records()
        history = self.read_history()

        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["id"], "bisa")
        self.assertEqual(current[0]["date"], "2026-11-23")
        self.assertEqual(current[0]["buy"], 6.85)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["id"], "bisa")

    def test_updates_same_entity_and_date_without_duplicate(self):
        entity = self.make_entity()

        first_quote = self.make_quote(
            buy="6.85",
            sell="6.96",
        )

        updated_quote = self.make_quote(
            buy="6.87",
            sell="6.98",
        )

        save_quote(entity, first_quote)
        save_quote(entity, updated_quote)

        current = self.read_current_records()
        history = self.read_history()

        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["buy"], 6.87)
        self.assertEqual(current[0]["sell"], 6.98)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["buy"], 6.87)
        self.assertEqual(history[0]["sell"], 6.98)

    def test_old_quote_does_not_replace_current_quote(self):
        entity = self.make_entity()

        latest_quote = self.make_quote(
            date="2026-11-23",
            buy="6.85",
            sell="6.96",
        )

        older_quote = self.make_quote(
            date="2026-11-20",
            buy="6.80",
            sell="6.90",
        )

        save_quote(entity, latest_quote)
        save_quote(entity, older_quote)

        current = self.read_current_records()
        history = self.read_history()

        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["date"], "2026-11-23")
        self.assertEqual(current[0]["buy"], 6.85)

        self.assertEqual(len(history), 2)

        history_dates = {record["date"] for record in history}

        self.assertEqual(
            history_dates,
            {"2026-11-20", "2026-11-23"},
        )

    def test_saves_different_entities_independently(self):
        bisa = self.make_entity("bisa", "Banco BISA")
        bcp = self.make_entity("bcp", "Banco de Crédito de Bolivia")

        save_quote(bisa, self.make_quote(buy="6.85", sell="6.96"))
        save_quote(bcp, self.make_quote(buy="6.80", sell="6.95"))

        current = self.read_current_records()

        bisa_history = self.read_history(entity_id="bisa")
        bcp_history = self.read_history(entity_id="bcp")

        current_ids = {
            record["id"]
            for record in current
        }

        self.assertEqual(current_ids, {"bisa", "bcp"})

        self.assertEqual(len(bisa_history), 1)
        self.assertEqual(len(bcp_history), 1)

        self.assertEqual(bisa_history[0]["id"], "bisa")
        self.assertEqual(bcp_history[0]["id"], "bcp")

    # ---------------------------------------------------------
    # Historical file structure
    # ---------------------------------------------------------

    def test_creates_year_directory_and_entity_file(self):
        entity = self.make_entity()

        save_quote(entity, self.make_quote())

        expected_file = (
            self.history_dir / "2026" / "bisa.jsonl"
        )

        self.assertTrue(expected_file.exists())

    def test_creates_separate_files_for_different_years(self):
        entity = self.make_entity()

        save_quote(entity, self.make_quote(date="2026-12-31"))
        save_quote(entity, self.make_quote(date="2027-01-01"))

        self.assertTrue(
            (self.history_dir / "2026" / "bisa.jsonl").exists()
        )

        self.assertTrue(
            (self.history_dir / "2027" / "bisa.jsonl").exists()
        )

    # ---------------------------------------------------------
    # Storage recovery
    # ---------------------------------------------------------

    def test_repair_restores_missing_history_from_current(self):
        entity = self.make_entity()

        save_quote(entity, self.make_quote())

        history_file = (
            self.history_dir / "2026" / "bisa.jsonl"
        )

        history_file.unlink()

        self.assertTrue(
            repair_quote_storage("bisa", "2026-11-23")
        )

        history = self.read_history()

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["id"], "bisa")

    def test_repair_restores_missing_current_from_history(self):
        entity = self.make_entity()

        save_quote(entity, self.make_quote())

        self.current_file.unlink()

        self.assertTrue(
            repair_quote_storage("bisa", "2026-11-23")
        )

        current = self.read_current_records()

        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["id"], "bisa")

    def test_get_current_and_history_record(self):
        entity = self.make_entity()

        save_quote(entity, self.make_quote())

        current = get_current_record("bisa", "2026-11-23")
        history = get_history_record("bisa", "2026-11-23")

        self.assertIsNotNone(current)
        self.assertIsNotNone(history)

        self.assertEqual(current["id"], "bisa")
        self.assertEqual(history["id"], "bisa")

    def test_repair_returns_false_when_both_records_are_missing(self):
        self.assertFalse(
            repair_quote_storage("bisa", "2026-11-23")
        )

    # ---------------------------------------------------------
    # Central bank and commercial bank quotation types
    # ---------------------------------------------------------

    def test_saves_central_bank_official_rate(self):
        entity = {
            "id": "bcb",
            "name": "Banco Central de Bolivia",
            "type": "central_bank",
        }

        save_quote(entity, self.make_bcb_quote())

        current = self.read_current_records()
        history = self.read_history(entity_id="bcb", year="2026")

        bcb_records = [
            record for record in current
            if record["id"] == "bcb"
        ]

        self.assertEqual(len(bcb_records), 1)
        self.assertEqual(bcb_records[0]["official_rate"], 11.75)

        self.assertNotIn("buy", bcb_records[0])
        self.assertNotIn("sell", bcb_records[0])

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["official_rate"], 11.75)

    def test_saves_commercial_bank_buy_and_sell(self):
        entity = {
            "id": "bisa",
            "name": "Banco BISA",
            "type": "commercial_bank",
        }

        save_quote(entity, self.make_bisa_quote())

        current = self.read_current_records()
        history = self.read_history(entity_id="bisa", year="2026")

        bisa_records = [
            record for record in current
            if record["id"] == "bisa"
        ]

        self.assertEqual(len(bisa_records), 1)
        self.assertEqual(bisa_records[0]["buy"], 6.85)
        self.assertEqual(bisa_records[0]["sell"], 6.96)

        self.assertNotIn("official_rate", bisa_records[0])

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

        current = self.read_current_records()

        bcb_history = self.read_history(
            entity_id="bcb",
            year="2026",
        )

        bisa_history = self.read_history(
            entity_id="bisa",
            year="2026",
        )

        current_by_id = {
            record["id"]: record
            for record in current
        }

        self.assertIn("bcb", current_by_id)
        self.assertIn("bisa", current_by_id)

        self.assertEqual(
            current_by_id["bcb"]["official_rate"],
            11.75,
        )

        self.assertEqual(current_by_id["bisa"]["buy"], 6.85)
        self.assertEqual(current_by_id["bisa"]["sell"], 6.96)

        self.assertEqual(len(bcb_history), 1)
        self.assertEqual(len(bisa_history), 1)

        self.assertEqual(bcb_history[0]["official_rate"], 11.75)
        self.assertEqual(bisa_history[0]["buy"], 6.85)
        self.assertEqual(bisa_history[0]["sell"], 6.96)

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

        current = self.read_current_records()

        history = self.read_history(
            entity_id="bcb",
            year="2026",
        )

        bcb_records = [
            record for record in current
            if record["id"] == "bcb"
        ]

        self.assertEqual(len(bcb_records), 1)
        self.assertEqual(bcb_records[0]["date"], "2026-11-23")
        self.assertEqual(bcb_records[0]["official_rate"], 11.75)

        self.assertEqual(len(history), 2)

        self.assertEqual(
            {record["date"] for record in history},
            {"2026-11-20", "2026-11-23"},
        )

    
    # ---------------------------------------------------------
    # Additional validation and recovery tests
    # ---------------------------------------------------------

    def test_rejects_non_iso_date_format(self):
        entity = self.make_entity()

        invalid_dates = [
            "2026-1-24",
            "2026/11/24",
            "24-11-2026",
            "20261124",
            "2026-02-30",
        ]

        for invalid_date in invalid_dates:
            with self.subTest(date=invalid_date):
                quote = self.make_quote(date=invalid_date)

                with self.assertRaises(ValueError):
                    save_quote(entity, quote)

    def test_rejects_invalid_records_in_current_data(self):
        self.current_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        invalid_data = {
            "updated_at": None,
            "currency": "USD",
            "price_currency": "BOB",
            "entities": [
                "bcb",
                None,
            ],
        }

        with self.current_file.open("w", encoding="utf-8") as file:
            json.dump(invalid_data, file)

        with self.assertRaises(ValueError):
            get_current_record("bcb")

    def test_rejects_duplicate_entity_ids_in_current_data(self):
        self.current_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        record = {
            "date": "2026-11-24",
            "captured_at": "2026-11-24T08:30:00-04:00",
            "id": "bisa",
            "name": "Banco BISA",
            "type": "commercial_bank",
            "buy": 6.85,
            "sell": 6.96,
        }

        data = {
            "updated_at": None,
            "currency": "USD",
            "price_currency": "BOB",
            "entities": [record, record.copy()],
        }

        with self.current_file.open("w", encoding="utf-8") as file:
            json.dump(data, file)

        with self.assertRaises(ValueError):
            get_current_record("bisa")

    def test_updated_at_uses_bolivia_timezone(self):
        entity = self.make_entity()

        save_quote(entity, self.make_quote())

        updated_at = self.read_current()["updated_at"]

        self.assertTrue(updated_at.endswith("-04:00"))

    def test_repair_preserves_newer_current_quote(self):
        entity = self.make_entity()

        older_quote = self.make_quote(
            date="2026-11-20",
            buy="6.80",
            sell="6.90",
        )

        newer_quote = self.make_quote(
            date="2026-11-24",
            buy="6.85",
            sell="6.96",
        )

        save_quote(entity, older_quote)
        save_quote(entity, newer_quote)

        self.assertTrue(
            repair_quote_storage("bisa", "2026-11-20")
        )

        current = self.read_current_records()
        history = self.read_history()

        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["date"], "2026-11-24")
        self.assertEqual(current[0]["buy"], 6.85)

        self.assertEqual(len(history), 2)
        self.assertEqual(
            {record["date"] for record in history},
            {"2026-11-20", "2026-11-24"},
        )


if __name__ == "__main__":
    unittest.main()
