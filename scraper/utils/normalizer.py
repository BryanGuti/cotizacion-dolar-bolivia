
import re
from decimal import Decimal, InvalidOperation


# Supported currency labels.
CURRENCY_LABELS = (
    r"BOB",
    r"BS\.?",
    r"BOLIVIANOS?",
)

# Build the currency label pattern separately.
CURRENCY_LABEL_PATTERN = "|".join(CURRENCY_LABELS)

CURRENCY_PATTERN = re.compile(
    rf"^(?:{CURRENCY_LABEL_PATTERN})\s*|\s*(?:{CURRENCY_LABEL_PATTERN})$",
    flags=re.IGNORECASE,
)

NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")


def normalize_rate(value) -> Decimal:
    """
    Convert an exchange rate into a normalized Decimal value.

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
        Decimal: normalized positive exchange rate.

    Raises:
        ValueError: if the input cannot be interpreted safely.
    """

    # 1. Reject invalid input types.
    if value is None or isinstance(value, bool):
        raise ValueError(
            "Exchange rate must be a valid numeric value."
        )

    # 2. Handle Decimal values.
    if isinstance(value, Decimal):
        result = value

    # 3. Handle integer and float values.
    elif isinstance(value, (int, float)):
        try:
            result = Decimal(str(value))

        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(
                f"Invalid exchange rate: {value!r}"
            ) from exc

    # 4. Handle strings.
    elif isinstance(value, str):
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("Exchange rate is empty.")

        # Remove an optional currency label at the beginning or end.
        cleaned = CURRENCY_PATTERN.sub("", cleaned).strip()

        if not cleaned:
            raise ValueError("Exchange rate is empty.")

        # Internal whitespace is not allowed.
        if re.search(r"\s", cleaned):
            raise ValueError(
                f"Invalid exchange rate format: {value!r}"
            )

        # Reject values containing both decimal separators.
        if "." in cleaned and "," in cleaned:
            raise ValueError(
                f"Ambiguous exchange rate format: {value!r}"
            )

        # Convert decimal comma into decimal point.
        if "," in cleaned:
            if cleaned.count(",") != 1:
                raise ValueError(
                    f"Ambiguous exchange rate format: {value!r}"
                )

            cleaned = cleaned.replace(",", ".")

        # Accept only standard positive decimal notation.
        if not NUMBER_PATTERN.fullmatch(cleaned):
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

    # 5. Reject non-finite values.
    if not result.is_finite():
        raise ValueError("Exchange rate must be finite.")

    # 6. Exchange rates must be strictly positive.
    if result <= 0:
        raise ValueError("Exchange rate must be greater than zero.")

    return result
