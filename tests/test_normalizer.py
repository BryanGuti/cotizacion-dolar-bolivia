
import unittest
from decimal import Decimal

from scraper.utils.normalizer import normalize_rate


class TestNormalizeRate(unittest.TestCase):

    # ---------------------------------------------------------
    # Valid numeric inputs
    # ---------------------------------------------------------

    def test_normalizes_integer(self):
        self.assertEqual(
            normalize_rate(6),
            Decimal("6"),
        )

    def test_normalizes_float(self):
        self.assertEqual(
            normalize_rate(6.96),
            Decimal("6.96"),
        )

    def test_normalizes_decimal(self):
        self.assertEqual(
            normalize_rate(Decimal("6.9600")),
            Decimal("6.9600"),
        )

    # ---------------------------------------------------------
    # Valid string inputs
    # ---------------------------------------------------------

    def test_normalizes_integer_string(self):
        self.assertEqual(
            normalize_rate("6"),
            Decimal("6"),
        )

    def test_normalizes_decimal_string(self):
        self.assertEqual(
            normalize_rate("6.96"),
            Decimal("6.96"),
        )

    def test_normalizes_decimal_comma(self):
        self.assertEqual(
            normalize_rate("6,96"),
            Decimal("6.96"),
        )

    def test_normalizes_string_with_leading_currency_label(self):
        self.assertEqual(
            normalize_rate("Bs. 6,96"),
            Decimal("6.96"),
        )

    def test_normalizes_string_with_currency_label_without_dot(self):
        self.assertEqual(
            normalize_rate("BS 6.96"),
            Decimal("6.96"),
        )

    def test_normalizes_string_with_trailing_currency_label(self):
        self.assertEqual(
            normalize_rate("6.96 BOB"),
            Decimal("6.96"),
        )

    def test_normalizes_string_with_lowercase_currency_label(self):
        self.assertEqual(
            normalize_rate("6.96 bob"),
            Decimal("6.96"),
        )

    def test_normalizes_string_with_bolivianos_label(self):
        self.assertEqual(
            normalize_rate("6,96 bolivianos"),
            Decimal("6.96"),
        )

    def test_normalizes_singular_boliviano_label(self):
        self.assertEqual(
            normalize_rate("6.96 BOLIVIANO"),
            Decimal("6.96"),
        )

    def test_normalizes_string_with_surrounding_whitespace(self):
        self.assertEqual(
            normalize_rate("  6.96  "),
            Decimal("6.96"),
        )

    # ---------------------------------------------------------
    # Invalid numeric inputs
    # ---------------------------------------------------------

    def test_rejects_none(self):
        with self.assertRaises(ValueError):
            normalize_rate(None)

    def test_rejects_boolean(self):
        for value in (True, False):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_rate(value)

    def test_rejects_negative_integer(self):
        with self.assertRaises(ValueError):
            normalize_rate(-6)

    def test_rejects_negative_float(self):
        with self.assertRaises(ValueError):
            normalize_rate(-6.96)

    def test_rejects_negative_decimal(self):
        with self.assertRaises(ValueError):
            normalize_rate(Decimal("-6.96"))

    def test_rejects_zero(self):
        for value in (0, 0.0, Decimal("0"), "0", "0.00"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_rate(value)

    def test_rejects_non_finite_decimal(self):
        invalid_values = (
            Decimal("NaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
        )

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_rate(value)

    def test_rejects_non_finite_float(self):
        invalid_values = (
            float("nan"),
            float("inf"),
            float("-inf"),
        )

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_rate(value)

    # ---------------------------------------------------------
    # Invalid string inputs
    # ---------------------------------------------------------

    def test_rejects_empty_string(self):
        for value in ("", " ", "   "):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_rate(value)

    def test_rejects_internal_whitespace(self):
        invalid_values = (
            "6 96",
            "6 .96",
            "6. 96",
            "6, 96",
        )

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_rate(value)

    def test_rejects_multiple_decimal_commas(self):
        with self.assertRaises(ValueError):
            normalize_rate("6,9,6")

    def test_rejects_mixed_decimal_separators(self):
        with self.assertRaises(ValueError):
            normalize_rate("6.96,00")

    def test_rejects_invalid_numeric_formats(self):
        invalid_values = (
            "-6.96",
            "+6.96",
            ".96",
            "6.",
            "6..96",
            "6abc",
            "abc6",
            "6/96",
            "6_96",
        )

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_rate(value)

    def test_rejects_invalid_currency_labels(self):
        invalid_values = (
            "USD 6.96",
            "6.96 USD",
            "Bs. USD 6.96",
            "6.96 BOB BOB",
        )

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_rate(value)

    # ---------------------------------------------------------
    # Unsupported input types
    # ---------------------------------------------------------

    def test_rejects_unsupported_input_types(self):
        invalid_values = (
            [],
            {},
            (),
            object(),
        )

        for value in invalid_values:
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    normalize_rate(value)


if __name__ == "__main__":
    unittest.main()
