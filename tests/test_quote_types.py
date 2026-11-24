
import unittest
from decimal import Decimal

from scraper.utils.validators import validate_quote


class TestQuotationTypes(unittest.TestCase):

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

    def test_valid_central_bank_quote(self):
        quote = {
            "date": "2026-11-23",
            "captured_at": "2026-11-23T08:00:00-04:00",
            "official_rate": Decimal("11.75"),
        }

        self.assertEqual(
            validate_quote(self.bcb, quote),
            (True, []),
        )

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

    def test_central_bank_rejects_buy_and_sell(self):
        quote = {
            "date": "2026-11-23",
            "captured_at": "2026-11-23T08:00:00-04:00",
            "buy": Decimal("11.75"),
            "sell": Decimal("11.75"),
        }

        is_valid, errors = validate_quote(self.bcb, quote)

        self.assertFalse(is_valid)
        self.assertTrue(
            any("must not contain buy or sell" in error for error in errors)
        )

    def test_central_bank_rejects_invalid_official_rate(self):
        quote = {
            "date": "2026-11-23",
            "captured_at": "2026-11-23T08:00:00-04:00",
            "official_rate": Decimal("0"),
        }

        is_valid, errors = validate_quote(self.bcb, quote)

        self.assertFalse(is_valid)
        self.assertIn(
            "official_rate must be a positive, finite numeric value.",
            errors,
        )

    def test_valid_commercial_bank_quote(self):
        quote = {
            "date": "2026-11-23",
            "captured_at": "2026-11-23T08:00:00-04:00",
            "buy": Decimal("6.85"),
            "sell": Decimal("6.96"),
        }

        self.assertEqual(
            validate_quote(self.commercial_bank, quote),
            (True, []),
        )

    def test_commercial_bank_rejects_official_rate(self):
        quote = {
            "date": "2026-11-23",
            "captured_at": "2026-11-23T08:00:00-04:00",
            "official_rate": Decimal("11.75"),
        }

        is_valid, errors = validate_quote(
            self.commercial_bank,
            quote,
        )

        self.assertFalse(is_valid)
        self.assertTrue(
            any("must not contain official_rate" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
