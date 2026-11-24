
import unittest
from datetime import datetime
from decimal import Decimal

from scraper.sources.base import (
    build_official_quote,
    build_quote,
)


class TestScraperBase(unittest.TestCase):

    def test_build_commercial_bank_quote(self):
        quote = build_quote(
            raw_buy="Bs. 6,85",
            raw_sell="6.96 BOB",
            quote_date="2026-11-23",
        )

        self.assertEqual(quote["date"], "2026-11-23")
        self.assertEqual(quote["buy"], Decimal("6.85"))
        self.assertEqual(quote["sell"], Decimal("6.96"))

        self.assertNotIn("official_rate", quote)

    def test_build_central_bank_quote(self):
        quote = build_official_quote(
            raw_rate="11,75",
            quote_date="2026-11-23",
        )

        self.assertEqual(quote["date"], "2026-11-23")
        self.assertEqual(
            quote["official_rate"],
            Decimal("11.75"),
        )

        self.assertNotIn("buy", quote)
        self.assertNotIn("sell", quote)

    def test_capture_timestamp_has_bolivia_timezone(self):
        quote = build_official_quote(
            raw_rate="11.75",
            quote_date="2026-11-23",
        )

        captured_at = datetime.fromisoformat(
            quote["captured_at"]
        )

        self.assertIsNotNone(captured_at.tzinfo)

        self.assertEqual(
            captured_at.utcoffset().total_seconds(),
            -4 * 60 * 60,
        )

    def test_empty_official_quote_date_is_rejected(self):
        with self.assertRaises(ValueError):
            build_official_quote(
                raw_rate="11.75",
                quote_date="",
            )

    def test_empty_commercial_quote_date_is_rejected(self):
        with self.assertRaises(ValueError):
            build_quote(
                raw_buy="6.85",
                raw_sell="6.96",
                quote_date="",
            )


if __name__ == "__main__":
    unittest.main()
