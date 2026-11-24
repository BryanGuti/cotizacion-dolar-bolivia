
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scraper.sources.registry import get_scraper, has_scraper


class TestScraperRegistry(unittest.TestCase):

    # ---------------------------------------------------------
    # has_scraper()
    # ---------------------------------------------------------

    def test_has_scraper_returns_true_for_registered_entities(self):
        self.assertTrue(has_scraper("bcb"))
        self.assertTrue(has_scraper("bmsc"))
        self.assertTrue(has_scraper("fortaleza"))

    def test_has_scraper_returns_false_for_unregistered_entity(self):
        self.assertFalse(has_scraper("unknown_bank"))

    def test_has_scraper_returns_false_for_invalid_entity_ids(self):
        invalid_ids = [
            None,
            "",
            "   ",
            [],
            {},
            123,
        ]

        for entity_id in invalid_ids:
            with self.subTest(entity_id=entity_id):
                self.assertFalse(has_scraper(entity_id))

    # ---------------------------------------------------------
    # get_scraper()
    # ---------------------------------------------------------

    def test_unknown_entity_raises_key_error(self):
        with patch(
            "scraper.sources.registry.SCRAPER_MODULES",
            {},
        ):
            with self.assertRaises(KeyError):
                get_scraper("unknown_bank")

    def test_invalid_entity_id_raises_key_error(self):
        invalid_ids = [
            None,
            "",
            "   ",
            [],
            {},
            123,
        ]

        for entity_id in invalid_ids:
            with self.subTest(entity_id=entity_id):
                with self.assertRaises(KeyError):
                    get_scraper(entity_id)

    def test_registered_scraper_is_returned(self):
        def fake_scrape(entity, source):
            return {"buy": 6.85}

        fake_module = SimpleNamespace(scrape=fake_scrape)

        with (
            patch(
                "scraper.sources.registry.SCRAPER_MODULES",
                {"bisa": "scraper.sources.bisa"},
            ),
            patch(
                "scraper.sources.registry.import_module",
                return_value=fake_module,
            ),
        ):
            scraper = get_scraper("bisa")

        self.assertIs(scraper, fake_scrape)

    def test_module_import_error_is_propagated(self):
        with (
            patch(
                "scraper.sources.registry.SCRAPER_MODULES",
                {"bisa": "scraper.sources.bisa"},
            ),
            patch(
                "scraper.sources.registry.import_module",
                side_effect=ImportError("Module not found"),
            ),
        ):
            with self.assertRaises(ImportError):
                get_scraper("bisa")

    def test_module_without_scrape_raises_attribute_error(self):
        fake_module = SimpleNamespace()

        with (
            patch(
                "scraper.sources.registry.SCRAPER_MODULES",
                {"bisa": "scraper.sources.bisa"},
            ),
            patch(
                "scraper.sources.registry.import_module",
                return_value=fake_module,
            ),
        ):
            with self.assertRaises(AttributeError):
                get_scraper("bisa")

    def test_non_callable_scrape_raises_type_error(self):
        fake_module = SimpleNamespace(
            scrape="not_a_function"
        )

        with (
            patch(
                "scraper.sources.registry.SCRAPER_MODULES",
                {"bisa": "scraper.sources.bisa"},
            ),
            patch(
                "scraper.sources.registry.import_module",
                return_value=fake_module,
            ),
        ):
            with self.assertRaises(TypeError):
                get_scraper("bisa")


if __name__ == "__main__":
    unittest.main()
