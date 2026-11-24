
from scraper.config import ENTITIES, SOURCES
from scraper.sources.registry import get_scraper, has_scraper
from scraper.utils.logger import get_logger
from scraper.utils.progress import (
    get_today,
    load_progress,
    is_entity_completed,
    update_entity_status,
)
from scraper.utils.validators import validate_quote
from scraper.utils.storage import save_quote


logger = get_logger(__name__)


def validate_configuration() -> bool:
    """Validate the basic project configuration."""

    logger.info("Validating scraper configuration...")

    if not ENTITIES:
        logger.error("No entities configured.")
        return False

    entity_ids = [entity["id"] for entity in ENTITIES]

    if len(entity_ids) != len(set(entity_ids)):
        logger.error("Duplicate entity IDs detected.")
        return False

    for entity in ENTITIES:
        entity_id = entity["id"]
        entity_name = entity["name"]

        if entity_id not in SOURCES:
            logger.warning(
                "No data source configured for %s (%s).",
                entity_name,
                entity_id,
            )
            continue

        source = SOURCES[entity_id]

        if not source.get("url"):
            logger.warning(
                "No URL configured for %s (%s).",
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


def process_quote(entity: dict, quote: dict, progress: dict) -> bool:
    """
    Validate and save a quotation.

    An entity is marked as successful only after its quotation
    has been validated and saved.
    """

    entity_id = entity["id"]
    entity_name = entity["name"]

    logger.info("Processing quotation for %s...", entity_name)

    is_valid, errors = validate_quote(entity, quote)

    if not is_valid:
        logger.error(
            "Invalid quotation for %s (%s):",
            entity_name,
            entity_id,
        )

        for error in errors:
            logger.error(" - %s", error)

        update_entity_status(progress, entity_id, "failed")
        return False

    try:
        save_quote(entity, quote)

    except Exception:
        logger.exception(
            "Could not save quotation for %s (%s).",
            entity_name,
            entity_id,
        )

        update_entity_status(progress, entity_id, "failed")
        return False

    update_entity_status(progress, entity_id, "success")

    logger.info(
        "Quotation successfully saved for %s (%s).",
        entity_name,
        entity_id,
    )

    return True


def main() -> None:
    """Run the daily exchange-rate scraping workflow."""

    logger.info("=" * 60)
    logger.info("Starting USD exchange rate scraper")
    logger.info("=" * 60)

    if not validate_configuration():
        logger.error("Configuration validation failed.")
        return

    today = get_today()
    progress = load_progress(today)

    logger.info("Execution date: %s", today)
    logger.info("Configured entities: %d", len(ENTITIES))

    processed_count = 0
    skipped_count = 0
    pending_count = 0
    failed_count = 0

    for entity in ENTITIES:
        entity_id = entity["id"]
        entity_name = entity["name"]

        # Skip entities already processed successfully today.
        if is_entity_completed(progress, entity_id):
            logger.info(
                "Skipping %s (%s): already completed today.",
                entity_name,
                entity_id,
            )
            skipped_count += 1
            continue

        # Check whether a source is configured.
        source = SOURCES.get(entity_id)

        if not source or not source.get("url"):
            logger.warning(
                "Skipping %s (%s): missing source configuration.",
                entity_name,
                entity_id,
            )
            update_entity_status(progress, entity_id, "failed")
            failed_count += 1
            continue

        # Check whether an individual scraper is implemented.
        if not has_scraper(entity_id):
            logger.info(
                "Skipping %s (%s): scraper not implemented yet.",
                entity_name,
                entity_id,
            )
            pending_count += 1
            continue

        # Retrieve and execute the entity-specific scraper.
        try:
            scraper = get_scraper(entity_id)

            logger.info(
                "Scraping quotation for %s (%s)...",
                entity_name,
                entity_id,
            )

            quote = scraper(entity, source)

            if not isinstance(quote, dict):
                raise ValueError(
                    "Scraper must return a dictionary containing the quotation."
                )

        except Exception:
            logger.exception(
                "Scraping failed for %s (%s).",
                entity_name,
                entity_id,
            )

            update_entity_status(progress, entity_id, "failed")
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

            update_entity_status(progress, entity_id, "failed")
            failed_count += 1
            continue

        if success:
            processed_count += 1
        else:
            failed_count += 1

    # Execution summary.
    logger.info("-" * 60)
    logger.info("Execution summary")
    logger.info("Already completed: %d", skipped_count)
    logger.info("Successfully processed: %d", processed_count)
    logger.info("Not implemented yet: %d", pending_count)
    logger.info("Failed: %d", failed_count)
    logger.info("Total entities: %d", len(ENTITIES))
    logger.info("-" * 60)

    logger.info("Scraper execution finished.")


if __name__ == "__main__":
    main()
