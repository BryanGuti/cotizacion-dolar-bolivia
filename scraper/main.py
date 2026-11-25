import time
from decimal import Decimal, InvalidOperation

import requests

from scraper.config import ENTITIES, SOURCES
from scraper.sources.registry import get_scraper, has_scraper
from scraper.utils.logger import get_logger, SUCCESS_LEVEL
from scraper.utils.validators import (
    VALID_ENTITY_TYPES,
    validate_quote,
)
from scraper.utils.storage import get_current_record, save_quote

logger = get_logger(__name__)

SCRAPE_MAX_ATTEMPTS = 3
SCRAPE_RETRY_BASE_DELAY_SECONDS = 1


def fetch_quote_with_retries(
    scraper,
    entity: dict,
    source: dict,
) -> dict:
    """Retry transient connection failures without accepting stale data."""

    for attempt in range(1, SCRAPE_MAX_ATTEMPTS + 1):
        try:
            quote = scraper(entity, source)

            if not isinstance(quote, dict):
                raise ValueError(
                    "Scraper must return a dictionary containing "
                    "the quotation."
                )

            return quote

        except (requests.ConnectionError, requests.Timeout) as exc:
            if attempt == SCRAPE_MAX_ATTEMPTS:
                raise

            delay = SCRAPE_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            logger.warning(
                "Temporary network error for %s (%s), attempt %d/%d: %s. "
                "Retrying in %d second(s).",
                entity["name"],
                entity["id"],
                attempt,
                SCRAPE_MAX_ATTEMPTS,
                exc,
                delay,
            )
            time.sleep(delay)

    raise RuntimeError("Scraper retry loop exited unexpectedly.")


def changed_rate_keys(
    entity: dict,
    previous_quote: dict | None,
    quote: dict,
) -> tuple[str, ...]:
    """Return commercial quote fields whose numeric values really changed."""

    if (
        entity.get("type") != "commercial_bank"
        or previous_quote is None
        or previous_quote.get("date") != quote.get("date")
    ):
        return ()

    changed = []
    for key in ("buy", "sell"):
        try:
            previous_value = Decimal(str(previous_quote.get(key)))
            current_value = Decimal(str(quote.get(key)))
        except (InvalidOperation, TypeError, ValueError):
            continue

        if (
            previous_value.is_finite()
            and current_value.is_finite()
            and previous_value != current_value
        ):
            changed.append(key)

    return tuple(changed)


def validate_configuration() -> bool:
    """Validate the basic project configuration."""

    logger.info("Validating scraper configuration...")

    if not isinstance(ENTITIES, (list, tuple)) or not ENTITIES:
        logger.error("Entities configuration must be a non-empty list.")
        return False

    if not isinstance(SOURCES, dict):
        logger.error("Sources configuration must be a dictionary.")
        return False

    entity_ids = []

    for index, entity in enumerate(ENTITIES):
        if not isinstance(entity, dict):
            logger.error(
                "Invalid entity configuration at position %d: "
                "expected a dictionary.",
                index,
            )
            return False

        entity_id = entity.get("id")
        entity_name = entity.get("name")
        entity_type = entity.get("type")

        if not isinstance(entity_id, str) or not entity_id.strip():
            logger.error(
                "Invalid entity ID at position %d.",
                index,
            )
            return False

        if not isinstance(entity_name, str) or not entity_name.strip():
            logger.error(
                "Invalid entity name for entity %s.",
                entity_id,
            )
            return False

        if entity_type not in VALID_ENTITY_TYPES:
            logger.error(
                "Invalid entity type for %s (%s).",
                entity_name,
                entity_id,
            )
            return False

        entity_ids.append(entity_id)

    if len(entity_ids) != len(set(entity_ids)):
        logger.error("Duplicate entity IDs detected.")
        return False

    for entity in ENTITIES:
        entity_id = entity["id"]
        entity_name = entity["name"]
        source = SOURCES.get(entity_id)

        if not isinstance(source, dict):
            logger.warning(
                "No valid data source configured for %s (%s).",
                entity_name,
                entity_id,
            )
            continue

        url = source.get("url")

        if not isinstance(url, str) or not url.strip():
            logger.warning(
                "No valid URL configured for %s (%s).",
                entity_name,
                entity_id,
            )
            continue

        logger.info(
            "Configuration found: %s (%s).",
            entity_name,
            entity_id,
        )

    return True


def process_quote(
    entity: dict,
    quote: dict,
) -> bool:
    """
    Validate and save a quotation.

    A quote is successful only after it has been validated and saved.
    """

    entity_id = entity["id"]
    entity_name = entity["name"]

    logger.info(
        "Validating quotation for %s (%s)...",
        entity_name,
        entity_id,
    )

    is_valid, errors = validate_quote(entity, quote)

    if not is_valid:
        logger.error(
            "Quotation validation failed for %s (%s):",
            entity_name,
            entity_id,
        )

        for error in errors:
            logger.error("  - %s", error)

        return False

    try:
        save_quote(entity, quote)

    except Exception:
        logger.exception(
            "Could not save quotation for %s (%s).",
            entity_name,
            entity_id,
        )

        return False

    logger.log(
        SUCCESS_LEVEL,
        "Quotation successfully saved for %s (%s).",
        entity_name,
        entity_id,
    )

    return True


def log_execution_summary(
    processed: int,
    pending: int,
    failed: int,
    total: int,
    updated_today: int = 0,
) -> None:
    """Display a summary of the scraping execution."""

    separator = "=" * 60

    logger.info(separator)
    logger.info("EXECUTION SUMMARY")
    logger.info(separator)

    logger.info("Total entities:           %d", total)
    logger.info("Successfully processed:   %d", processed)
    logger.info("Not implemented:          %d", pending)
    logger.info("Failed:                   %d", failed)
    logger.info("Updated today:            %d", updated_today)

    logger.info(separator)

    if failed:
        logger.error(
            "Execution finished with %d failure(s).",
            failed,
        )

    elif pending:
        logger.warning(
            "Execution finished with %d scraper(s) not implemented.",
            pending,
        )

    else:
        logger.log(
            SUCCESS_LEVEL,
            "Execution completed successfully.",
        )


def main() -> int:
    """Run the scraper and return a failing status for incomplete runs."""

    separator = "=" * 60

    logger.info(separator)
    logger.info("USD EXCHANGE RATE SCRAPER")
    logger.info(separator)

    if not validate_configuration():
        logger.critical("Configuration validation failed.")
        return 1

    logger.info("Configured entities: %d", len(ENTITIES))
    logger.info("-" * 60)

    processed_count = 0
    pending_count = 0
    failed_count = 0
    updated_today_count = 0

    for entity in ENTITIES:
        entity_id = entity["id"]
        entity_name = entity["name"]

        logger.info(
            "Processing entity: %s (%s)",
            entity_name,
            entity_id,
        )

        # Check whether a valid source is configured.
        source = SOURCES.get(entity_id)

        if (
            not isinstance(source, dict)
            or not isinstance(source.get("url"), str)
            or not source["url"].strip()
        ):
            logger.error(
                "Missing or invalid source configuration for %s (%s).",
                entity_name,
                entity_id,
            )

            failed_count += 1
            continue

        # Check whether an individual scraper is implemented.
        if not has_scraper(entity_id):
            logger.warning(
                "[PENDING] %s (%s): scraper not implemented yet.",
                entity_name,
                entity_id,
            )

            pending_count += 1
            continue

        # Retrieve and execute the entity-specific scraper.
        try:
            scraper = get_scraper(entity_id)

            logger.info(
                "Fetching quotation from source for %s (%s)...",
                entity_name,
                entity_id,
            )

            quote = fetch_quote_with_retries(scraper, entity, source)

        except Exception:
            logger.exception(
                "Scraping failed for %s (%s).",
                entity_name,
                entity_id,
            )

            failed_count += 1
            continue

        # Validate and persist the quotation.
        try:
            previous_quote = get_current_record(entity_id)
            changed_keys = changed_rate_keys(entity, previous_quote, quote)
            changed_today = bool(changed_keys)
            success = process_quote(entity, quote)

        except Exception:
            logger.exception(
                "Unexpected error processing %s (%s).",
                entity_name,
                entity_id,
            )

            failed_count += 1
            continue

        if success:
            processed_count += 1
            if changed_today:
                updated_today_count += 1
                changes = ", ".join(
                    f"{key}: {previous_quote[key]} → {quote[key]}"
                    for key in changed_keys
                )
                logger.log(
                    SUCCESS_LEVEL,
                    "[UPDATED] %s (%s) changed today: %s",
                    entity_name,
                    entity_id,
                    changes,
                )
        else:
            failed_count += 1

    log_execution_summary(
        processed=processed_count,
        pending=pending_count,
        failed=failed_count,
        total=len(ENTITIES),
        updated_today=updated_today_count,
    )

    return 1 if failed_count or pending_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
