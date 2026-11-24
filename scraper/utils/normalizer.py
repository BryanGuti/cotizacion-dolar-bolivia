
import re
from decimal import Decimal, InvalidOperation


# Supported currency labels
CURRENCY_LABELS = (
    r"BOB",
    r"BS\.?",
    r"BOLIVIANOS?",
)

CURRENCY_PATTERN = re.compile(
    rf"^(?:{'|'.join(CURRENCY_LABELS)})\s*"
    rf"|\s*(?:{'|'.join(CURRENCY_LABELS)})$",
    flags=re.IGNORECASE,
)


def normalize_rate(value) -> Decimal:
    """
    Converts an exchange rate into a normalized Decimal value.

    Supported examples:
        6.96
        6.9600
        "6.96"
        "6,96"
        "Bs. 6,96"
        "BS. 6,96"
        "bs 6.96"
        "6.96 BOB"
        "6.96 bob"
        "6,96 bolivianos"
        "6.96 BOLIVIANO"

    Returns:
        Decimal: normalized exchange rate.

    Raises:
        ValueError: if the input cannot be interpreted safely.
    """

    # 1. Reject invalid input types
    if value is None or isinstance(value, bool):
        raise ValueError(
            "Exchange rate must be a valid numeric value."
        )

    # 2. Handle Decimal values
    if isinstance(value, Decimal):
        result = value

    # 3. Handle integer and float values
    elif isinstance(value, (int, float)):
        try:
            result = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError(
                f"Invalid exchange rate: {value!r}"
            ) from exc

    # 4. Handle strings
    elif isinstance(value, str):
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("Exchange rate is empty.")

        # Remove currency labels at the beginning or end
        cleaned = CURRENCY_PATTERN.sub("", cleaned).strip()

        # Remove internal whitespace
        cleaned = re.sub(r"\s+", "", cleaned)

        if not cleaned:
            raise ValueError("Exchange rate is empty.")

        # Reject values containing both decimal separators
        if "." in cleaned and "," in cleaned:
            raise ValueError(
                f"Ambiguous exchange rate format: {value!r}"
            )

        # Convert decimal comma into decimal point
        if "," in cleaned:
            if cleaned.count(",") != 1:
                raise ValueError(
                    f"Ambiguous exchange rate format: {value!r}"
                )

            cleaned = cleaned.replace(",", ".")

        # Accept only standard positive decimal notation
        if not re.fullmatch(r"\d+(?:\.\d+)?", cleaned):
            raise ValueError(
                f"Invalid exchange rate format: {value!r}"
            )

        try:
            result = Decimal(cleaned)
        except InvalidOperation as exc:
            raise ValueError(
                f"Invalid exchange rate: {value!r}"
            ) from exc

    else:
        raise ValueError(
            f"Unsupported exchange rate type: {type(value).__name__}"
        )

    # 5. Reject non-finite values
    if not result.is_finite():
        raise ValueError("Exchange rate must be finite.")

    return result
