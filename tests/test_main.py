import unittest
from unittest.mock import Mock, patch

from scraper import main


class TestMain(unittest.TestCase):

    def setUp(self):
        self.entity = {
            "id": "bisa",
            "name": "Banco BISA",
            "type": "commercial_bank",
        }

        self.source = {
            "url": "https://example.com",
            "method": "requests",
        }

        self.quote = {
            "date": "2026-11-24",
            "captured_at": "2026-11-24T08:30:00-04:00",
            "buy": 6.85,
            "sell": 6.96,
        }

        self.progress = {
            "date": "2026-11-24",
            "entities": {},
        }

        self.scraper = Mock(return_value=self.quote)

        self.patches = [
            patch.object(main, "ENTITIES", [self.entity]),
            patch.object(
                main,
                "SOURCES",
                {"bisa": self.source},
            ),
            patch.object(
                main,
                "get_today",
                return_value="2026-11-24",
            ),
            patch.object(
                main,
                "load_progress",
                return_value=self.progress,
            ),
            patch.object(
                main,
                "is_entity_completed",
                side_effect=lambda progress, entity_id: (
                    progress["entities"].get(entity_id) == "success"
                ),
            ),
            patch.object(
                main,
                "repair_quote_storage",
                return_value=False,
            ),
            patch.object(
                main,
                "has_scraper",
                return_value=True,
            ),
            patch.object(
                main,
                "get_scraper",
                return_value=self.scraper,
            ),
            patch.object(
                main,
                "validate_quote",
                return_value=(True, []),
            ),
            patch.object(main, "save_quote"),
            patch.object(
                main,
                "update_entity_status",
                side_effect=self.update_status,
            ),
        ]

        self.mocks = [
            item.start()
            for item in self.patches
        ]

        (
            self.entities_mock,
            self.sources_mock,
            self.today_mock,
            self.progress_mock,
            self.completed_mock,
            self.repair_mock,
            self.has_scraper_mock,
            self.get_scraper_mock,
            self.validate_mock,
            self.save_mock,
            self.update_mock,
        ) = self.mocks

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()

    def update_status(self, progress, entity_id, status):
        progress["entities"][entity_id] = status

    # ---------------------------------------------------------
    # Configuration validation
    # ---------------------------------------------------------

    def test_validate_configuration_accepts_valid_configuration(self):
        self.assertTrue(main.validate_configuration())

    def test_validate_configuration_rejects_empty_entities(self):
        with patch.object(main, "ENTITIES", []):
            self.assertFalse(main.validate_configuration())

    def test_validate_configuration_rejects_non_list_entities(self):
        with patch.object(main, "ENTITIES", None):
            self.assertFalse(main.validate_configuration())

    def test_validate_configuration_rejects_non_dictionary_entity(self):
        with patch.object(main, "ENTITIES", ["bisa"]):
            self.assertFalse(main.validate_configuration())

    def test_validate_configuration_rejects_missing_entity_id(self):
        invalid_entity = {
            "name": "Banco BISA",
            "type": "commercial_bank",
        }

        with patch.object(main, "ENTITIES", [invalid_entity]):
            self.assertFalse(main.validate_configuration())

    def test_validate_configuration_rejects_empty_entity_name(self):
        invalid_entity = {
            "id": "bisa",
            "name": " ",
            "type": "commercial_bank",
        }

        with patch.object(main, "ENTITIES", [invalid_entity]):
            self.assertFalse(main.validate_configuration())

    def test_validate_configuration_rejects_invalid_entity_type(self):
        invalid_entity = {
            "id": "bisa",
            "name": "Banco BISA",
            "type": "unknown",
        }

        with patch.object(main, "ENTITIES", [invalid_entity]):
            self.assertFalse(main.validate_configuration())

    def test_validate_configuration_rejects_duplicate_entity_ids(self):
        duplicated_entities = [
            self.entity,
            {
                "id": "bisa",
                "name": "Another Bank",
                "type": "commercial_bank",
            },
        ]

        with patch.object(
            main,
            "ENTITIES",
            duplicated_entities,
        ):
            self.assertFalse(main.validate_configuration())

    def test_validate_configuration_rejects_invalid_sources_container(self):
        with patch.object(main, "SOURCES", None):
            self.assertFalse(main.validate_configuration())

    # ---------------------------------------------------------
    # Successful execution and storage recovery
    # ---------------------------------------------------------

    def test_successful_entity_with_complete_storage_is_skipped(self):
        self.progress["entities"]["bisa"] = "success"
        self.repair_mock.return_value = True

        main.main()

        self.repair_mock.assert_called_once_with(
            "bisa",
            "2026-11-24",
        )

        self.scraper.assert_not_called()
        self.save_mock.assert_not_called()

    def test_successful_entity_with_repaired_storage_is_skipped(self):
        self.progress["entities"]["bisa"] = "success"
        self.repair_mock.return_value = True

        main.main()

        self.repair_mock.assert_called_once()
        self.scraper.assert_not_called()

    def test_successful_entity_with_missing_storage_is_scraped(self):
        self.progress["entities"]["bisa"] = "success"
        self.repair_mock.return_value = False

        main.main()

        self.repair_mock.assert_called_once()

        self.scraper.assert_called_once_with(
            self.entity,
            self.source,
        )

        self.save_mock.assert_called_once_with(
            self.entity,
            self.quote,
        )

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "success",
        )

    def test_entity_without_success_is_scraped_even_if_storage_exists(self):
        self.progress["entities"].pop("bisa", None)
        self.repair_mock.return_value = True

        main.main()

        # Storage verification is only used after a previous success.
        self.repair_mock.assert_not_called()

        self.scraper.assert_called_once()

        self.save_mock.assert_called_once_with(
            self.entity,
            self.quote,
        )

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "success",
        )

    def test_entity_with_failed_status_is_scraped_again(self):
        self.progress["entities"]["bisa"] = "failed"

        main.main()

        self.repair_mock.assert_not_called()
        self.scraper.assert_called_once()
        self.save_mock.assert_called_once()

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "success",
        )

    def test_storage_verification_error_does_not_prevent_scraping(self):
        self.progress["entities"]["bisa"] = "success"

        self.repair_mock.side_effect = OSError(
            "Storage could not be read."
        )

        main.main()

        self.scraper.assert_called_once()
        self.save_mock.assert_called_once()

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "success",
        )

    # ---------------------------------------------------------
    # Source and scraper availability
    # ---------------------------------------------------------

    def test_entity_without_source_is_marked_as_failed(self):
        self.sources_mock.clear()

        main.main()

        self.scraper.assert_not_called()
        self.save_mock.assert_not_called()

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "failed",
        )

    def test_entity_with_empty_source_url_is_marked_as_failed(self):
        self.sources_mock["bisa"] = {
            "url": " ",
            "method": "requests",
        }

        main.main()

        self.scraper.assert_not_called()
        self.save_mock.assert_not_called()

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "failed",
        )

    def test_entity_with_invalid_source_structure_is_marked_as_failed(self):
        self.sources_mock["bisa"] = "invalid"

        main.main()

        self.scraper.assert_not_called()

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "failed",
        )

    def test_entity_without_registered_scraper_is_pending(self):
        self.has_scraper_mock.return_value = False

        main.main()

        self.scraper.assert_not_called()
        self.save_mock.assert_not_called()
        self.update_mock.assert_not_called()

    def test_scraper_registry_error_marks_entity_as_failed(self):
        self.get_scraper_mock.side_effect = ImportError(
            "Scraper module could not be loaded."
        )

        main.main()

        self.scraper.assert_not_called()
        self.save_mock.assert_not_called()

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "failed",
        )

    # ---------------------------------------------------------
    # Scraping errors
    # ---------------------------------------------------------

    def test_scraper_error_marks_entity_as_failed(self):
        self.scraper.side_effect = RuntimeError(
            "Connection failed."
        )

        main.main()

        self.scraper.assert_called_once()
        self.save_mock.assert_not_called()

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "failed",
        )

    def test_scraper_returning_non_dictionary_marks_entity_failed(self):
        self.scraper.return_value = None

        main.main()

        self.save_mock.assert_not_called()

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "failed",
        )

    # ---------------------------------------------------------
    # Quotation validation and persistence
    # ---------------------------------------------------------

    def test_invalid_quote_marks_entity_as_failed(self):
        self.validate_mock.return_value = (
            False,
            ["Invalid exchange rate."],
        )

        main.main()

        self.scraper.assert_called_once()
        self.save_mock.assert_not_called()

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "failed",
        )

    def test_save_error_marks_entity_as_failed(self):
        self.save_mock.side_effect = OSError(
            "Could not write quotation."
        )

        main.main()

        self.save_mock.assert_called_once()

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "failed",
        )

    def test_progress_update_error_does_not_interrupt_processing(self):
        self.update_mock.side_effect = OSError(
            "Could not write progress."
        )

        main.main()

        self.scraper.assert_called_once()
        self.save_mock.assert_called_once()

        # The quotation was saved successfully even though
        # the progress update failed.
        self.validate_mock.assert_called_once()

    # ---------------------------------------------------------
    # Independent entity processing
    # ---------------------------------------------------------

    def test_failure_in_one_entity_does_not_stop_the_next(self):
        second_entity = {
            "id": "bmsc",
            "name": "Banco Mercantil Santa Cruz",
            "type": "commercial_bank",
        }

        second_source = {
            "url": "https://example.org",
            "method": "requests",
        }

        second_quote = {
            "date": "2026-11-24",
            "captured_at": "2026-11-24T09:00:00-04:00",
            "buy": 6.80,
            "sell": 6.90,
        }

        self.entities_mock[:] = [
            self.entity,
            second_entity,
        ]

        self.sources_mock["bmsc"] = second_source

        self.scraper.side_effect = [
            RuntimeError("First bank failed."),
            second_quote,
        ]

        main.main()

        self.assertEqual(
            self.scraper.call_count,
            2,
        )

        self.save_mock.assert_called_once_with(
            second_entity,
            second_quote,
        )

        self.assertEqual(
            self.progress["entities"]["bisa"],
            "failed",
        )

        self.assertEqual(
            self.progress["entities"]["bmsc"],
            "success",
        )


if __name__ == "__main__":
    unittest.main()
