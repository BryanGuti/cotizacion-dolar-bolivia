
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


VALID_ENTITY_TYPES = {
    "central_bank",
    "commercial_bank",
}


def _is_valid_rate(value) -> bool:
    """Check whether a quotation rate is a positive finite number."""

    if isinstance(value, bool):
        return False

    try:
        rate = Decimal(str(value))

    except (InvalidOperation, ValueError, TypeError):
        return False

    return rate.is_finite() and rate > 0


def _is_valid_date(value) -> bool:
    """Check whether a date uses the exact YYYY-MM-DD format."""

    if not isinstance(value, str):
        return False

    try:
        parsed_date = date.fromisoformat(value)

    except ValueError:
        return False

    return parsed_date.isoformat() == value


def _is_valid_timestamp(value) -> bool:
    """Check whether a timestamp is ISO 8601 and includes a timezone."""

    if not isinstance(value, str):
        return False

    try:
        captured_at = datetime.fromisoformat(value)

    except ValueError:
        return False

    return (
        captured_at.tzinfo is not None
        and captured_at.utcoffset() is not None
    )


def validate_quote(entity: dict, quote: dict) -> tuple[bool, list[str]]:
    """
    Validate a quotation according to the entity type.

    Central banks:
        date, captured_at, official_rate

    Commercial banks:
        date, captured_at, buy, sell

    Returns:
        tuple[bool, list[str]]:
            Whether the quotation is valid and a list of validation errors.
    """

    errors = []

    # 1. Validate the entity structure.
    if not isinstance(entity, dict):
        return False, ["Entity must be a dictionary."]

    required_entity_fields = ("id", "name", "type")

    for field in required_entity_fields:
        value = entity.get(field)

        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"Missing entity field: {field}"
            )

    entity_type = entity.get("type")

    if (
        not isinstance(entity_type, str)
        or entity_type not in VALID_ENTITY_TYPES
    ):
        errors.append("Invalid entity type.")

    # 2. Validate the quotation structure.
    if not isinstance(quote, dict):
        errors.append("Quotation must be a dictionary.")
        return False, errors

    # 3. Validate common quotation fields.
    common_fields = ("date", "captured_at")

    for field in common_fields:
        if field not in quote:
            errors.append(
                f"Missing quotation field: {field}"
            )

    # 4. Determine entity-specific quotation fields.
    if entity_type == "central_bank":
        rate_fields = ("official_rate",)

        if "buy" in quote or "sell" in quote:
            errors.append(
                "Central bank quotations must not contain buy or sell."
            )

    elif entity_type == "commercial_bank":
        rate_fields = ("buy", "sell")

        if "official_rate" in quote:
            errors.append(
                "Commercial bank quotations must not contain official_rate."
            )

    else:
        rate_fields = ()

    for field in rate_fields:
        if field not in quote:
            errors.append(
                f"Missing quotation field: {field}"
            )

    # 5. Stop if required fields are missing or structures are invalid.
    if errors:
        return False, errors

    # 6. Validate quotation date.
    if not _is_valid_date(quote["date"]):
        errors.append(
            "Invalid quotation date. Expected YYYY-MM-DD."
        )

    # 7. Validate capture timestamp.
    if not _is_valid_timestamp(quote["captured_at"]):
        errors.append(
            "Invalid capture timestamp. Expected ISO 8601 with timezone."
        )

    # 8. Validate entity-specific exchange rates.
    for field in rate_fields:
        if not _is_valid_rate(quote[field]):
            errors.append(
                f"{field} must be a positive, finite numeric value."
            )

    return len(errors) == 0, errors
