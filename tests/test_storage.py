
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from scraper.utils.storage import save_quote


class TestStorage(unittest.TestCase):

    def setUp(self):
        # Cada prueba utiliza su propio directorio temporal.
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.current_file = self.temp_path / "current.json"
        self.history_dir = self.temp_path / "history"

        # Redirigimos el almacenamiento para no tocar los archivos reales.
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

    def read_current(self):
        with self.current_file.open("r", encoding="utf-8") as file:
            return json.load(file)

    def read_history(self, year="2026"):
        history_file = self.history_dir / f"{year}.jsonl"

        with history_file.open("r", encoding="utf-8") as file:
            return [
                json.loads(line)
                for line in file
                if line.strip()
            ]

    def test_saves_new_quote(self):
        entity = self.make_entity()
        quote = self.make_quote()

        save_quote(entity, quote)

        current = self.read_current()
        history = self.read_history()

        self.assertEqual(len(current["entities"]), 1)
        self.assertEqual(current["entities"][0]["id"], "bisa")
        self.assertEqual(current["entities"][0]["date"], "2026-11-23")
        self.assertEqual(current["entities"][0]["buy"], 6.85)

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

        current = self.read_current()
        history = self.read_history()

        self.assertEqual(len(current["entities"]), 1)
        self.assertEqual(current["entities"][0]["buy"], 6.87)
        self.assertEqual(current["entities"][0]["sell"], 6.98)

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

        current = self.read_current()
        history = self.read_history()

        self.assertEqual(len(current["entities"]), 1)
        self.assertEqual(current["entities"][0]["date"], "2026-11-23")
        self.assertEqual(current["entities"][0]["buy"], 6.85)

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

        current = self.read_current()
        history = self.read_history()

        current_ids = {
            record["id"]
            for record in current["entities"]
        }

        history_ids = {
            record["id"]
            for record in history
        }

        self.assertEqual(current_ids, {"bisa", "bcp"})
        self.assertEqual(history_ids, {"bisa", "bcp"})
        self.assertEqual(len(current["entities"]), 2)
        self.assertEqual(len(history), 2)


if __name__ == "__main__":
    unittest.main()
