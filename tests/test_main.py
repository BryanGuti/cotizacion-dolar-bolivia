import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from scraper import main
from scraper.utils import storage


def http_error(status_code, headers=None):
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}
    return requests.HTTPError(
        f"HTTP {status_code}",
        response=response,
    )


class TestMain(unittest.TestCase):

    def setUp(self):
        self.entity = {
            "id": "bisa",
            "name": "Banco BISA",
            "type": "commercial_bank",
        }

        self.source = {
            "url": "https://example.com",
        }

        self.quote = {
            "date": "2026-11-24",
            "captured_at": "2026-11-24T08:30:00-04:00",
            "buy": 6.85,
            "sell": 6.96,
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
        ]

        self.mocks = [
            item.start()
            for item in self.patches
        ]

        (
            self.entities_mock,
            self.sources_mock,
            self.has_scraper_mock,
            self.get_scraper_mock,
            self.validate_mock,
            self.save_mock,
        ) = self.mocks

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()

    # ---------------------------------------------------------
    # Configuration validation
    # ---------------------------------------------------------

    def test_validate_configuration_accepts_valid_configuration(self):
        self.assertTrue(main.validate_configuration())

    def test_validate_configuration_rejects_empty_entities(self):
        with patch.object(main, "ENTITIES", []):
            self.assertFalse(main.validate_configuration())

    def test_invalid_configuration_returns_failure_status(self):
        with patch.object(main, "ENTITIES", []):
            self.assertEqual(main.main(), 1)

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
    # Successful execution
    # ---------------------------------------------------------

    def test_successful_entity_is_scraped_again_to_capture_updated_rates(self):
        self.assertEqual(main.main(), 0)

        self.scraper.assert_called_once_with(self.entity, self.source)
        self.save_mock.assert_called_once_with(self.entity, self.quote)

    def test_summary_counts_same_day_rate_changes(self):
        previous = {
            "date": self.quote["date"],
            "buy": 6.80,
            "sell": 6.90,
        }
        with patch.object(main, "get_current_record", return_value=previous), \
                patch.object(main, "log_execution_summary") as summary, \
                patch.object(main.logger, "log") as log:
            main.main()

        self.assertEqual(summary.call_args.kwargs["updated_today"], 1)
        self.assertTrue(any(
            call.args[1].startswith("[UPDATED]")
            for call in log.call_args_list
            if len(call.args) > 1 and isinstance(call.args[1], str)
        ))

    def test_same_day_unchanged_decimal_rates_are_not_marked_updated(self):
        previous = {
            "date": self.quote["date"],
            "buy": 6.85,
            "sell": 6.96,
        }
        from decimal import Decimal
        decimal_quote = {**self.quote, "buy": Decimal("6.85"), "sell": Decimal("6.96")}

        self.assertEqual(
            main.changed_rate_keys(self.entity, previous, decimal_quote),
            (),
        )

    def test_change_to_either_same_day_bank_rate_is_detected(self):
        previous = {"date": self.quote["date"], "buy": 6.85, "sell": 6.96}
        quote = {**self.quote, "buy": 6.85, "sell": 6.97}

        self.assertEqual(
            main.changed_rate_keys(self.entity, previous, quote),
            ("sell",),
        )

    # ---------------------------------------------------------
    # Source and scraper availability
    # ---------------------------------------------------------

    def test_entity_without_source_is_not_scraped(self):
        self.sources_mock.clear()

        main.main()

        self.scraper.assert_not_called()
        self.save_mock.assert_not_called()

    def test_entity_with_empty_source_url_is_not_scraped(self):
        self.sources_mock["bisa"] = {
            "url": " ",
        }

        main.main()

        self.scraper.assert_not_called()
        self.save_mock.assert_not_called()

    def test_entity_with_invalid_source_structure_is_not_scraped(self):
        self.sources_mock["bisa"] = "invalid"

        main.main()

        self.scraper.assert_not_called()

    def test_entity_without_registered_scraper_is_pending(self):
        self.has_scraper_mock.return_value = False

        self.assertEqual(main.main(), 1)

        self.scraper.assert_not_called()
        self.save_mock.assert_not_called()

    def test_scraper_registry_error_does_not_save_quote(self):
        self.get_scraper_mock.side_effect = ImportError(
            "Scraper module could not be loaded."
        )

        main.main()

        self.scraper.assert_not_called()
        self.save_mock.assert_not_called()

    # ---------------------------------------------------------
    # Scraping errors
    # ---------------------------------------------------------

    def test_scraper_error_does_not_save_quote(self):
        self.scraper.side_effect = RuntimeError(
            "Connection failed."
        )

        self.assertEqual(main.main(), 1)

        self.scraper.assert_called_once()
        self.save_mock.assert_not_called()

    def test_transient_connection_error_retries_and_succeeds(self):
        self.scraper.side_effect = [
            requests.ConnectionError("Connection reset by peer."),
            self.quote,
        ]

        with patch.object(main.time, "sleep") as sleep, patch.object(
            main.random, "uniform", return_value=0.5
        ):
            self.assertEqual(main.main(), 0)

        self.assertEqual(self.scraper.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in sleep.call_args_list],
            [3.5],
        )
        self.save_mock.assert_called_once_with(self.entity, self.quote)

    def test_transient_timeout_retries_and_succeeds(self):
        self.scraper.side_effect = [
            requests.Timeout("Read timed out."),
            self.quote,
        ]

        with patch.object(main.time, "sleep") as sleep, patch.object(
            main.random, "uniform", return_value=0
        ):
            self.assertEqual(main.main(), 0)

        self.assertEqual(self.scraper.call_count, 2)
        sleep.assert_called_once_with(3)
        self.save_mock.assert_called_once_with(self.entity, self.quote)

    def test_transient_tls_error_retries_and_succeeds(self):
        self.scraper.side_effect = [
            requests.exceptions.SSLError("TLS handshake reset."),
            self.quote,
        ]

        with patch.object(main.time, "sleep"), patch.object(
            main.random, "uniform", return_value=0
        ):
            self.assertEqual(main.main(), 0)

        self.assertEqual(self.scraper.call_count, 2)
        self.save_mock.assert_called_once_with(self.entity, self.quote)

    def test_persistent_connection_error_fails_after_retry_limit(self):
        self.scraper.side_effect = requests.ConnectionError(
            "Connection reset by peer."
        )

        with patch.object(main.time, "sleep") as sleep, patch.object(
            main.random, "uniform", return_value=0.5
        ):
            self.assertEqual(main.main(), 1)

        self.assertEqual(self.scraper.call_count, main.SCRAPE_MAX_ATTEMPTS)
        self.assertEqual(sleep.call_count, main.SCRAPE_MAX_ATTEMPTS - 1)
        self.assertEqual(
            [call.args[0] for call in sleep.call_args_list],
            [3.5, 7.5, 15.5, 30.5],
        )
        self.save_mock.assert_not_called()

    def test_http_429_respects_retry_after(self):
        self.scraper.side_effect = [
            http_error(429, {"Retry-After": "12"}),
            self.quote,
        ]

        with patch.object(main.time, "sleep") as sleep, patch.object(
            main.random, "uniform"
        ) as jitter:
            self.assertEqual(main.main(), 0)

        self.assertEqual(self.scraper.call_count, 2)
        sleep.assert_called_once_with(12.0)
        jitter.assert_not_called()
        self.save_mock.assert_called_once_with(self.entity, self.quote)

    def test_http_date_retry_after_is_respected(self):
        now = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
        retry_at = now + timedelta(seconds=45)
        error = http_error(
            503,
            {"Retry-After": format_datetime(retry_at, usegmt=True)},
        )

        with patch.object(main, "datetime") as datetime_mock:
            datetime_mock.now.return_value = now
            self.assertEqual(main._retry_after_seconds(error), 45)

    def test_http_5xx_retries(self):
        self.scraper.side_effect = [http_error(503), self.quote]

        with patch.object(main.time, "sleep") as sleep, patch.object(
            main.random, "uniform", return_value=0.25
        ):
            self.assertEqual(main.main(), 0)

        self.assertEqual(self.scraper.call_count, 2)
        sleep.assert_called_once_with(3.25)
        self.save_mock.assert_called_once_with(self.entity, self.quote)

    def test_permanent_http_4xx_is_not_retried(self):
        self.scraper.side_effect = http_error(403)

        with patch.object(main.time, "sleep") as sleep:
            self.assertEqual(main.main(), 1)

        self.scraper.assert_called_once_with(self.entity, self.source)
        sleep.assert_not_called()
        self.save_mock.assert_not_called()

    def test_retry_logging_includes_entity_attempt_and_delay(self):
        self.scraper.side_effect = [
            requests.ConnectionError("Connection reset."),
            self.quote,
        ]

        with patch.object(main.time, "sleep"), patch.object(
            main.random, "uniform", return_value=0.5
        ), patch.object(main.logger, "info") as info, patch.object(
            main.logger, "warning"
        ) as warning:
            self.assertEqual(main.main(), 0)

        attempt_logs = [
            call
            for call in info.call_args_list
            if call.args[0].startswith("Scrape attempt")
        ]
        self.assertEqual(
            [(call.args[1], call.args[2]) for call in attempt_logs],
            [(1, main.SCRAPE_MAX_ATTEMPTS), (2, main.SCRAPE_MAX_ATTEMPTS)],
        )
        self.assertEqual(
            warning.call_args.args[1:5],
            ("Banco BISA", "bisa", 1, main.SCRAPE_MAX_ATTEMPTS),
        )
        self.assertEqual(warning.call_args.args[-1], 3.5)

    def test_retry_then_success_writes_one_valid_history_record(self):
        self.scraper.side_effect = [
            requests.ConnectionError("Connection reset."),
            self.quote,
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_directory = Path(temporary_directory)
            current_file = data_directory / "current.json"
            history_directory = data_directory / "history"
            with patch.object(
                storage, "CURRENT_DATA_FILE", current_file
            ), patch.object(
                storage, "HISTORY_DIR", history_directory
            ), patch.object(
                main, "save_quote", side_effect=storage.save_quote
            ), patch.object(
                main.time, "sleep"
            ), patch.object(
                main.random, "uniform", return_value=0
            ):
                self.assertEqual(main.main(), 0)

            history_file = history_directory / "2026" / "bisa.jsonl"
            records = [
                json.loads(line)
                for line in history_file.read_text(encoding="utf-8").splitlines()
            ]
            current_data = json.loads(current_file.read_text(encoding="utf-8"))

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], self.entity["id"])
        self.assertEqual(len(current_data["entities"]), 1)
        self.assertEqual(current_data["entities"][0]["buy"], self.quote["buy"])

    def test_scraper_returning_non_dictionary_does_not_save_quote(self):
        self.scraper.return_value = None

        main.main()

        self.scraper.assert_called_once_with(self.entity, self.source)
        self.save_mock.assert_not_called()

    # ---------------------------------------------------------
    # Quotation validation and persistence
    # ---------------------------------------------------------

    def test_invalid_quote_is_not_saved(self):
        self.validate_mock.return_value = (
            False,
            ["Invalid exchange rate."],
        )

        main.main()

        self.scraper.assert_called_once()
        self.save_mock.assert_not_called()

    def test_save_error_is_handled(self):
        self.save_mock.side_effect = OSError(
            "Could not write quotation."
        )

        main.main()

        self.save_mock.assert_called_once()

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



if __name__ == "__main__":
    unittest.main()
