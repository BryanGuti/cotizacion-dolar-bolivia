
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scraper.config import PROGRESS_FILE
from scraper.utils.logger import get_logger


logger = get_logger(__name__)

TIMEZONE = ZoneInfo("America/La_Paz")

VALID_STATUSES = {
    "success",
    "failed",
}


def get_today() -> str:
    """Return the current date in Bolivia."""
    return datetime.now(TIMEZONE).date().isoformat()


def _new_progress(today: str) -> dict:
    """Create an empty progress structure."""
    return {
        "date": today,
        "entities": {},
    }


def _save_progress(progress: dict) -> None:
    """Save progress atomically to avoid partially written files."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=PROGRESS_FILE.parent,
            delete=False,
            newline="\n",
        ) as temp_file:
            temp_path = Path(temp_file.name)

            json.dump(
                progress,
                temp_file,
                ensure_ascii=False,
                indent=2,
            )

            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_path, PROGRESS_FILE)

    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _is_valid_progress(progress: dict) -> bool:
    """Validate the basic progress structure."""

    if not isinstance(progress, dict):
        return False

    if not isinstance(progress.get("date"), str):
        return False

    if not isinstance(progress.get("entities"), dict):
        return False

    return True


def load_progress(today: str | None = None) -> dict:
    """
    Load daily progress.

    If the file does not exist, belongs to another date,
    or contains invalid data, initialize a new progress file.
    """

    current_date = today or get_today()

    if not PROGRESS_FILE.exists():
        progress = _new_progress(current_date)
        _save_progress(progress)

        logger.info("Created new daily progress file.")
        return progress

    try:
        with PROGRESS_FILE.open("r", encoding="utf-8") as file:
            progress = json.load(file)

        if not _is_valid_progress(progress):
            raise ValueError("Invalid progress file structure.")

        if progress["date"] != current_date:
            progress = _new_progress(current_date)
            _save_progress(progress)

            logger.info("Daily progress reset for %s.", current_date)
            return progress

        entities = progress["entities"]

        valid_entities = {
            entity_id: status
            for entity_id, status in entities.items()
            if (
                isinstance(entity_id, str)
                and entity_id.strip()
                and isinstance(status, str)
                and status in VALID_STATUSES
            )
        }

        if valid_entities != entities:
            progress["entities"] = valid_entities
            _save_progress(progress)

            logger.warning(
                "Invalid progress entries were removed."
            )

        return progress

    except (json.JSONDecodeError, OSError, ValueError) as exc:
        logger.warning(
            "Could not read progress file. Starting fresh: %s",
            exc,
        )

        progress = _new_progress(current_date)
        _save_progress(progress)

        return progress


def is_entity_completed(progress: dict, entity_id: str) -> bool:
    """Return True only if the entity was successfully processed."""

    return progress["entities"].get(entity_id) == "success"


def update_entity_status(
    progress: dict,
    entity_id: str,
    status: str,
) -> None:
    """Update an entity status and persist the progress file."""

    if not isinstance(entity_id, str) or not entity_id.strip():
        raise ValueError("Entity ID must be a non-empty string.")

    if status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid progress status: {status!r}"
        )

    progress["entities"][entity_id] = status

    _save_progress(progress)

    logger.info(
        "Progress updated: %s -> %s",
        entity_id,
        status,
    )
