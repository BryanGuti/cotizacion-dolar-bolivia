
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

        if not isinstance(progress, dict):
            raise ValueError("Progress file must contain a JSON object.")

        if progress.get("date") != current_date:
            progress = _new_progress(current_date)
            _save_progress(progress)

            logger.info("Daily progress reset for %s.", current_date)
            return progress

        entities = progress.get("entities")

        if not isinstance(entities, dict):
            raise ValueError("Progress entities must be a dictionary.")

        # Keep only recognized statuses.
        progress["entities"] = {
            entity_id: status
            for entity_id, status in entities.items()
            if isinstance(status, str) and status in VALID_STATUSES
        }

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
