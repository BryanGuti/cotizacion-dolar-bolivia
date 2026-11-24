
from scraper.config import ENTITIES, SOURCES
from scraper.sources.registry import get_scraper, has_scraper
from scraper.utils.logger import get_logger, SUCCESS_LEVEL
from scraper.utils.progress import (
    get_today,
    load_progress,
    is_entity_completed,
    update_entity_status,
)
from scraper.utils.validators import (
    VALID_ENTITY_TYPES,
    validate_quote,
)
from scraper.utils.storage import repair_quote_storage, save_quote


logger = get_logger(__name__)


def _update_status_safely(
    progress: dict,
    entity_id: str,
    status: str,
) -> bool:
    """Update entity progress without interrupting the workflow."""

    try:
        update_entity_status(progress, entity_id, status)
        return True

    except Exception:
        logger.exception(
            "Could not update progress for entity %s to '%s'.",
            entity_id,
            status,
        )
        return False


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
    progress: dict,
) -> bool:
    """
    Validate and save a quotation.

    An entity is marked as successful only after its quotation
    has been validated and saved.
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

        _update_status_safely(progress, entity_id, "failed")
        return False

    try:
        save_quote(entity, quote)

    except Exception:
        logger.exception(
            "Could not save quotation for %s (%s).",
            entity_name,
            entity_id,
        )

        _update_status_safely(progress, entity_id, "failed")
        return False

    _update_status_safely(progress, entity_id, "success")

    logger.log(
        SUCCESS_LEVEL,
        "Quotation successfully saved for %s (%s).",
        entity_name,
        entity_id,
    )

    return True


def should_skip_entity(
    entity: dict,
    progress: dict,
    today: str,
) -> bool:
    """
    Decide whether an entity can be skipped.

    A successful progress status is not sufficient by itself.
    Both current and historical storage must be verified.
    Missing records are repaired whenever possible.
    """

    entity_id = entity["id"]
    entity_name = entity["name"]

    if not is_entity_completed(progress, entity_id):
        return False

    try:
        storage_is_complete = repair_quote_storage(
            entity_id,
            today,
        )

    except Exception:
        logger.exception(
            "Could not verify storage for %s (%s). "
            "The scraper will be executed.",
            entity_name,
            entity_id,
        )
        return False

    if storage_is_complete:
        logger.info(
            "[SKIPPED] %s (%s): today's quotation "
            "is already stored.",
            entity_name,
            entity_id,
        )
        return True

    logger.warning(
        "Storage is incomplete for %s (%s). "
        "The scraper will be executed.",
        entity_name,
        entity_id,
    )

    return False


def log_execution_summary(
    processed: int,
    skipped: int,
    pending: int,
    failed: int,
    total: int,
) -> None:
    """Display a summary of the scraping execution."""

    separator = "=" * 60

    logger.info(separator)
    logger.info("EXECUTION SUMMARY")
    logger.info(separator)

    logger.info("Total entities:           %d", total)
    logger.info("Successfully processed:   %d", processed)
    logger.info("Skipped (already stored): %d", skipped)
    logger.info("Not implemented:          %d", pending)
    logger.info("Failed:                   %d", failed)

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


def main() -> None:
    """Run the daily exchange-rate scraping workflow."""

    separator = "=" * 60

    logger.info(separator)
    logger.info("USD EXCHANGE RATE SCRAPER")
    logger.info(separator)

    if not validate_configuration():
        logger.critical("Configuration validation failed.")
        return

    today = get_today()
    progress = load_progress(today)

    logger.info("Execution date: %s", today)
    logger.info("Configured entities: %d", len(ENTITIES))
    logger.info("-" * 60)

    processed_count = 0
    skipped_count = 0
    pending_count = 0
    failed_count = 0

    for entity in ENTITIES:
        entity_id = entity["id"]
        entity_name = entity["name"]

        logger.info(
            "Processing entity: %s (%s)",
            entity_name,
            entity_id,
        )

        # Verify storage before skipping a successful entity.
        if should_skip_entity(entity, progress, today):
            skipped_count += 1
            continue

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

            _update_status_safely(
                progress,
                entity_id,
                "failed",
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

            quote = scraper(entity, source)

            if not isinstance(quote, dict):
                raise ValueError(
                    "Scraper must return a dictionary containing "
                    "the quotation."
                )

        except Exception:
            logger.exception(
                "Scraping failed for %s (%s).",
                entity_name,
                entity_id,
            )

            _update_status_safely(
                progress,
                entity_id,
                "failed",
            )
            failed_count += 1
            continue

        # Validate and persist the quotation.
        try:
            success = process_quote(entity, quote, progress)

        except Exception:
            logger.exception(
                "Unexpected error processing %s (%s).",
                entity_name,
                entity_id,
            )

            _update_status_safely(
                progress,
                entity_id,
                "failed",
            )
            failed_count += 1
            continue

        if success:
            processed_count += 1
        else:
            failed_count += 1

    log_execution_summary(
        processed=processed_count,
        skipped=skipped_count,
        pending=pending_count,
        failed=failed_count,
        total=len(ENTITIES),
    )


if __name__ == "__main__":
    main()
