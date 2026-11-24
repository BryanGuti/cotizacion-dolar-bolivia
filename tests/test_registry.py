
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scraper.sources.registry import get_scraper, has_scraper


class TestScraperRegistry(unittest.TestCase):

    def test_unknown_entity_raises_key_error(self):
        with patch(
            "scraper.sources.registry.SCRAPER_MODULES",
            {},
        ):
            with self.assertRaises(KeyError):
                get_scraper("unknown_bank")

    def test_registered_scraper_is_returned(self):
        fake_scrape = lambda entity, source: {"buy": 6.85}

        fake_module = SimpleNamespace(
            scrape=fake_scrape
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
            scraper = get_scraper("bisa")

        self.assertIs(scraper, fake_scrape)

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

    def test_has_scraper_returns_true_for_registered_entity(self):
        assert has_scraper("bcb") is True
        assert has_scraper("bmsc") is True

    def test_has_scraper_returns_false_for_unregistered_entity(self):
        assert has_scraper("nonexistent") is False

    def test_has_scraper_returns_false_for_unknown_entity(self):
        assert has_scraper("unknown") is False


if __name__ == "__main__":
    unittest.main()
