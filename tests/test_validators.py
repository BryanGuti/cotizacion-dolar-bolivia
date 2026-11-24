
import unittest
from decimal import Decimal

from scraper.utils.validators import (
    _is_valid_rate,
    validate_quote,
)


class TestQuotationValidation(unittest.TestCase):

    def setUp(self):
        self.bcb = {
            "id": "bcb",
            "name": "Banco Central de Bolivia",
            "type": "central_bank",
        }

        self.commercial_bank = {
            "id": "bisa",
            "name": "Banco BISA",
            "type": "commercial_bank",
        }

        self.bcb_quote = {
            "date": "2026-11-23",
            "captured_at": "2026-11-23T08:00:00-04:00",
            "official_rate": Decimal("11.75"),
        }

        self.commercial_quote = {
            "date": "2026-11-23",
            "captured_at": "2026-11-23T08:00:00-04:00",
            "buy": Decimal("6.85"),
            "sell": Decimal("6.96"),
        }

    # ---------------------------------------------------------
    # Valid quotation types
    # ---------------------------------------------------------

    def test_valid_central_bank_quote(self):
        self.assertEqual(
            validate_quote(self.bcb, self.bcb_quote),
            (True, []),
        )

    def test_valid_commercial_bank_quote(self):
        self.assertEqual(
            validate_quote(self.commercial_bank, self.commercial_quote),
            (True, []),
        )

    # ---------------------------------------------------------
    # Entity validation
    # ---------------------------------------------------------

    def test_rejects_non_dictionary_entity(self):
        is_valid, errors = validate_quote(
            [],
            self.bcb_quote,
        )

        self.assertFalse(is_valid)
        self.assertIn("Entity must be a dictionary.", errors)

    def test_rejects_missing_entity_fields(self):
        invalid_entities = (
            {"name": "Banco BISA", "type": "commercial_bank"},
            {"id": "bisa", "type": "commercial_bank"},
            {"id": "bisa", "name": "Banco BISA"},
        )

        for entity in invalid_entities:
            with self.subTest(entity=entity):
                is_valid, errors = validate_quote(
                    entity,
                    self.commercial_quote,
                )

                self.assertFalse(is_valid)
                self.assertTrue(errors)

    def test_rejects_empty_entity_fields(self):
        fields = ("id", "name", "type")

        for field in fields:
            with self.subTest(field=field):
                entity = self.commercial_bank.copy()
                entity[field] = ""

                is_valid, errors = validate_quote(
                    entity,
                    self.commercial_quote,
                )

                self.assertFalse(is_valid)
                self.assertTrue(errors)

    def test_rejects_whitespace_entity_fields(self):
        fields = ("id", "name", "type")

        for field in fields:
            with self.subTest(field=field):
                entity = self.commercial_bank.copy()
                entity[field] = "   "

                is_valid, errors = validate_quote(
                    entity,
                    self.commercial_quote,
                )

                self.assertFalse(is_valid)
                self.assertTrue(errors)

    def test_rejects_non_string_entity_fields(self):
        invalid_values = (
            123,
            [],
            {},
            None,
        )

        for field in ("id", "name", "type"):
            for value in invalid_values:
                with self.subTest(field=field, value=value):
                    entity = self.commercial_bank.copy()
                    entity[field] = value

                    is_valid, errors = validate_quote(
                        entity,
                        self.commercial_quote,
                    )

                    self.assertFalse(is_valid)
                    self.assertTrue(errors)

    def test_rejects_invalid_entity_type(self):
        entity = self.commercial_bank.copy()
        entity["type"] = "unknown"

        is_valid, errors = validate_quote(
            entity,
            self.commercial_quote,
        )

        self.assertFalse(is_valid)
        self.assertIn("Invalid entity type.", errors)

    def test_rejects_unhashable_entity_type(self):
        invalid_values = ([], {}, None)

        for value in invalid_values:
            with self.subTest(value=value):
                entity = self.commercial_bank.copy()
                entity["type"] = value

                is_valid, errors = validate_quote(
                    entity,
                    self.commercial_quote,
                )

                self.assertFalse(is_valid)
                self.assertIn("Invalid entity type.", errors)

    # ---------------------------------------------------------
    # Quotation structure validation
    # ---------------------------------------------------------

    def test_rejects_non_dictionary_quote(self):
        is_valid, errors = validate_quote(
            self.bcb,
            [],
        )

        self.assertFalse(is_valid)
        self.assertIn("Quotation must be a dictionary.", errors)

    def test_central_bank_quote_without_official_rate(self):
        quote = {
            "date": "2026-11-23",
            "captured_at": "2026-11-23T08:00:00-04:00",
        }

        is_valid, errors = validate_quote(self.bcb, quote)

        self.assertFalse(is_valid)
        self.assertIn(
            "Missing quotation field: official_rate",
            errors,
        )

    def test_commercial_bank_quote_without_buy(self):
        quote = {
            "date": "2026-11-23",
            "captured_at": "2026-11-23T08:00:00-04:00",
            "sell": Decimal("6.96"),
        }

        is_valid, errors = validate_quote(
            self.commercial_bank,
            quote,
        )

        self.assertFalse(is_valid)
        self.assertIn("Missing quotation field: buy", errors)

    def test_commercial_bank_quote_without_sell(self):
        quote = {
            "date": "2026-11-23",
            "captured_at": "2026-11-23T08:00:00-04:00",
            "buy": Decimal("6.85"),
        }

        is_valid, errors = validate_quote(
            self.commercial_bank,
            quote,
        )

        self.assertFalse(is_valid)
        self.assertIn("Missing quotation field: sell", errors)

    def test_central_bank_rejects_buy_and_sell(self):
        quote = self.bcb_quote.copy()
        quote["buy"] = Decimal("11.75")
        quote["sell"] = Decimal("11.75")

        is_valid, errors = validate_quote(self.bcb, quote)

        self.assertFalse(is_valid)
        self.assertTrue(
            any(
                "must not contain buy or sell" in error
                for error in errors
            )
        )

    def test_commercial_bank_rejects_official_rate(self):
        quote = self.commercial_quote.copy()
        quote["official_rate"] = Decimal("11.75")

        is_valid, errors = validate_quote(
            self.commercial_bank,
            quote,
        )

        self.assertFalse(is_valid)
        self.assertTrue(
            any(
                "must not contain official_rate" in error
                for error in errors
            )
        )

    # ---------------------------------------------------------
    # Date validation
    # ---------------------------------------------------------

    def test_accepts_valid_date(self):
        self.assertEqual(
            validate_quote(self.bcb, self.bcb_quote),
            (True, []),
        )

    def test_rejects_invalid_date_formats(self):
        invalid_dates = (
            "2026-1-23",
            "2026/11/23",
            "23-11-2026",
            "20261123",
            "2026-02-30",
            "2026-13-01",
            "",
            " ",
            None,
            20261123,
        )

        for value in invalid_dates:
            with self.subTest(date=value):
                quote = self.bcb_quote.copy()
                quote["date"] = value

                is_valid, errors = validate_quote(
                    self.bcb,
                    quote,
                )

                self.assertFalse(is_valid)
                self.assertIn(
                    "Invalid quotation date. Expected YYYY-MM-DD.",
                    errors,
                )

    # ---------------------------------------------------------
    # Capture timestamp validation
    # ---------------------------------------------------------

    def test_accepts_timestamp_with_timezone(self):
        valid_timestamps = (
            "2026-11-23T08:00:00-04:00",
            "2026-11-23T12:00:00+00:00",
            "2026-11-23T12:00:00Z",
        )

        for value in valid_timestamps:
            with self.subTest(timestamp=value):
                quote = self.bcb_quote.copy()
                quote["captured_at"] = value

                self.assertEqual(
                    validate_quote(self.bcb, quote),
                    (True, []),
                )

    def test_rejects_timestamp_without_timezone(self):
        quote = self.bcb_quote.copy()
        quote["captured_at"] = "2026-11-23T08:00:00"

        is_valid, errors = validate_quote(self.bcb, quote)

        self.assertFalse(is_valid)
        self.assertIn(
            "Invalid capture timestamp. Expected ISO 8601 with timezone.",
            errors,
        )

    def test_rejects_invalid_timestamps(self):
        invalid_timestamps = (
            "",
            " ",
            "2026/11/23 08:00:00",
            "not-a-timestamp",
            "2026-13-23T08:00:00-04:00",
            None,
            123,
            [],
        )

        for value in invalid_timestamps:
            with self.subTest(timestamp=value):
                quote = self.bcb_quote.copy()
                quote["captured_at"] = value

                is_valid, errors = validate_quote(
                    self.bcb,
                    quote,
                )

                self.assertFalse(is_valid)
                self.assertTrue(
                    any(
                        "Invalid capture timestamp" in error
                        for error in errors
                    )
                )

    # ---------------------------------------------------------
    # Rate validation
    # ---------------------------------------------------------

    def test_accepts_valid_rates(self):
        valid_values = (
            6,
            6.96,
            Decimal("6.96"),
            "6.96",
        )

        for value in valid_values:
            with self.subTest(value=value):
                self.assertTrue(_is_valid_rate(value))

    def test_rejects_invalid_rates(self):
        invalid_values = (
            None,
            True,
            False,
            0,
            0.0,
            Decimal("0"),
            -1,
            -6.96,
            Decimal("-6.96"),
            "",
            "invalid",
            Decimal("NaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
            float("nan"),
            float("inf"),
            float("-inf"),
            [],
            {},
        )

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(_is_valid_rate(value))

    def test_central_bank_rejects_invalid_official_rate(self):
        invalid_values = (
            Decimal("0"),
            Decimal("-1"),
            Decimal("NaN"),
            Decimal("Infinity"),
            None,
            True,
            "invalid",
        )

        for value in invalid_values:
            with self.subTest(value=value):
                quote = self.bcb_quote.copy()
                quote["official_rate"] = value

                is_valid, errors = validate_quote(
                    self.bcb,
                    quote,
                )

                self.assertFalse(is_valid)
                self.assertIn(
                    "official_rate must be a positive, finite numeric value.",
                    errors,
                )

    def test_commercial_bank_rejects_invalid_buy_rate(self):
        quote = self.commercial_quote.copy()
        quote["buy"] = Decimal("0")

        is_valid, errors = validate_quote(
            self.commercial_bank,
            quote,
        )

        self.assertFalse(is_valid)
        self.assertIn(
            "buy must be a positive, finite numeric value.",
            errors,
        )

    def test_commercial_bank_rejects_invalid_sell_rate(self):
        quote = self.commercial_quote.copy()
        quote["sell"] = Decimal("-1")

        is_valid, errors = validate_quote(
            self.commercial_bank,
            quote,
        )

        self.assertFalse(is_valid)
        self.assertIn(
            "sell must be a positive, finite numeric value.",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
