
from datetime import datetime
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


def validate_quote(entity: dict, quote: dict) -> tuple[bool, list[str]]:
    """
    Validate a quotation according to the entity type.

    Central banks:
        date, captured_at, official_rate

    Commercial banks:
        date, captured_at, buy, sell
    """

    errors = []

    if not isinstance(entity, dict):
        return False, ["Entity must be a dictionary."]

    required_entity_fields = ("id", "name", "type")

    for field in required_entity_fields:
        if not entity.get(field):
            errors.append(f"Missing entity field: {field}")

    entity_type = entity.get("type")

    if entity_type not in VALID_ENTITY_TYPES:
        errors.append("Invalid entity type.")

    if not isinstance(quote, dict):
        errors.append("Quotation must be a dictionary.")
        return False, errors

    # Common fields for all quotation types.
    required_fields = ("date", "captured_at")

    for field in required_fields:
        if field not in quote:
            errors.append(f"Missing quotation field: {field}")

    # Entity-specific quotation fields.
    if entity_type == "central_bank":
        required_fields = ("official_rate",)

        if "buy" in quote or "sell" in quote:
            errors.append(
                "Central bank quotations must not contain buy or sell."
            )

    elif entity_type == "commercial_bank":
        required_fields = ("buy", "sell")

        if "official_rate" in quote:
            errors.append(
                "Commercial bank quotations must not contain official_rate."
            )

    else:
        required_fields = ()

    for field in required_fields:
        if field not in quote:
            errors.append(f"Missing quotation field: {field}")

    if errors:
        return False, errors

    # Validate quotation date.
    try:
        datetime.strptime(quote["date"], "%Y-%m-%d")
    except (TypeError, ValueError):
        errors.append("Invalid quotation date. Expected YYYY-MM-DD.")

    # Validate capture timestamp.
    try:
        captured_at = datetime.fromisoformat(quote["captured_at"])

        if captured_at.tzinfo is None or captured_at.utcoffset() is None:
            errors.append(
                "Capture timestamp must include a timezone."
            )

    except (TypeError, ValueError):
        errors.append(
            "Invalid capture timestamp. Expected ISO 8601."
        )

    # Validate entity-specific rates.
    for field in required_fields:
        if field in quote and not _is_valid_rate(quote[field]):
            errors.append(
                f"{field} must be a positive, finite numeric value."
            )

    return len(errors) == 0, errors
