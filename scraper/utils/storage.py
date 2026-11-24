
import json
import os
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from scraper.config import (
    CURRENT_DATA_FILE,
    HISTORY_DIR,
    CURRENCY,
    PRICE_CURRENCY,
)


TIMEZONE = ZoneInfo("America/La_Paz")


def _json_compatible(value):
    """Convert Decimal values into JSON-compatible numbers."""

    if isinstance(value, Decimal):
        return float(value)

    raise TypeError(
        f"Unsupported JSON data type: {type(value).__name__}"
    )


def _validate_date(value: str) -> str:
    """Validate and return a date in exact YYYY-MM-DD format."""

    if not isinstance(value, str):
        raise ValueError("Date must be a string in YYYY-MM-DD format.")

    try:
        parsed_date = date.fromisoformat(value)

    except ValueError as exc:
        raise ValueError(
            f"Invalid date format: {value!r}. Expected YYYY-MM-DD."
        ) from exc

    if parsed_date.isoformat() != value:
        raise ValueError(
            f"Invalid date format: {value!r}. Expected YYYY-MM-DD."
        )

    return value


def _atomic_write(path: Path, content: str) -> None:
    """Write a file atomically to avoid partially written data."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
            newline="\n",
        ) as temp_file:
            temp_path = Path(temp_file.name)

            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_path, path)

    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _read_current_data() -> dict:
    """Read and validate current quotation data."""

    if not CURRENT_DATA_FILE.exists():
        return {
            "updated_at": None,
            "currency": CURRENCY,
            "price_currency": PRICE_CURRENCY,
            "entities": [],
        }

    with CURRENT_DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("current.json must contain a JSON object.")

    entities = data.get("entities")

    if not isinstance(entities, list):
        raise ValueError("current.json must contain an entities list.")

    seen_ids = set()

    for index, record in enumerate(entities):
        if not isinstance(record, dict):
            raise ValueError(
                f"Invalid entity record at index {index} in current.json."
            )

        entity_id = record.get("id")

        if not isinstance(entity_id, str) or not entity_id.strip():
            raise ValueError(
                f"Invalid entity ID at index {index} in current.json."
            )

        if entity_id in seen_ids:
            raise ValueError(
                f"Duplicate entity ID in current.json: {entity_id}"
            )

        seen_ids.add(entity_id)

        _validate_date(record.get("date"))

    return data


def _write_current_data(data: dict) -> None:
    """Serialize and atomically save current quotation data."""

    content = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        default=_json_compatible,
    )

    _atomic_write(CURRENT_DATA_FILE, content + "\n")


def _build_record(entity: dict, quote: dict) -> dict:
    """
    Build a historical/current record according to entity type.

    Central banks use official_rate.
    Commercial banks use buy and sell.
    """

    record_date = _validate_date(quote["date"])

    record = {
        "date": record_date,
        "captured_at": quote["captured_at"],
        "id": entity["id"],
        "name": entity["name"],
        "type": entity["type"],
    }

    if entity["type"] == "central_bank":
        record["official_rate"] = quote["official_rate"]

    elif entity["type"] == "commercial_bank":
        record["buy"] = quote["buy"]
        record["sell"] = quote["sell"]

    else:
        raise ValueError(
            f"Unsupported entity type: {entity['type']}"
        )

    return record


def _update_current(record: dict) -> bool:
    """
    Insert or update an entity's latest quotation.

    An older quotation never replaces a newer one.

    Returns:
        True if current.json was modified.
        False if the incoming quotation was older.
    """

    data = _read_current_data()
    entities = data["entities"]

    existing_index = next(
        (
            index
            for index, item in enumerate(entities)
            if item["id"] == record["id"]
        ),
        None,
    )

    if existing_index is None:
        entities.append(record)

    else:
        existing_record = entities[existing_index]

        if record["date"] < existing_record["date"]:
            return False

        entities[existing_index] = record

    data["updated_at"] = datetime.now(TIMEZONE).isoformat()
    data["currency"] = CURRENCY
    data["price_currency"] = PRICE_CURRENCY

    _write_current_data(data)

    return True


def _history_file_path(entity_id: str, year: str) -> Path:
    """Return the historical file path for an entity and year."""

    if (
        not isinstance(entity_id, str)
        or not entity_id
        or Path(entity_id).name != entity_id
        or entity_id in {".", ".."}
    ):
        raise ValueError(f"Invalid entity ID: {entity_id!r}")

    if (
        not isinstance(year, str)
        or len(year) != 4
        or not year.isdigit()
    ):
        raise ValueError(f"Invalid history year: {year!r}")

    return HISTORY_DIR / year / f"{entity_id}.jsonl"


def _read_history(path: Path) -> list[dict]:
    """Read and validate all records from a JSONL history file."""

    if not path.exists():
        return []

    records = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):

            if not line.strip():
                continue

            try:
                record = json.loads(line)

            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path}, line {line_number}."
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Invalid record in {path}, line {line_number}."
                )

            try:
                _validate_date(record.get("date"))

            except ValueError as exc:
                raise ValueError(
                    f"Invalid date in {path}, line {line_number}."
                ) from exc

            records.append(record)

    return records


def _update_history(record: dict) -> None:
    """
    Insert or replace a historical record.

    Each entity can have only one record per date.
    """

    record_date = _validate_date(record["date"])
    year = record_date[:4]

    history_file = _history_file_path(record["id"], year)
    records = _read_history(history_file)

    updated = False

    for index, existing in enumerate(records):

        if existing.get("date") == record_date:
            records[index] = record
            updated = True
            break

    if not updated:
        records.append(record)

    records.sort(key=lambda item: item["date"])

    content = "".join(
        json.dumps(
            item,
            ensure_ascii=False,
            default=_json_compatible,
        ) + "\n"
        for item in records
    )

    _atomic_write(history_file, content)


def get_current_record(
    entity_id: str,
    record_date: str | None = None,
) -> dict | None:
    """
    Retrieve an entity's current record.

    If record_date is provided, only return the record
    when its date matches.
    """

    if record_date is not None:
        _validate_date(record_date)

    data = _read_current_data()

    for record in data["entities"]:

        if record["id"] != entity_id:
            continue

        if record_date is not None:
            if record["date"] != record_date:
                return None

        return record

    return None


def get_history_record(
    entity_id: str,
    record_date: str,
) -> dict | None:
    """Retrieve an entity's historical record for a specific date."""

    _validate_date(record_date)

    year = record_date[:4]
    history_file = _history_file_path(entity_id, year)

    records = _read_history(history_file)

    for record in records:
        if record.get("date") == record_date:
            return record

    return None


def repair_quote_storage(
    entity_id: str,
    record_date: str,
) -> bool:
    """
    Verify and repair current/history storage consistency.

    If current contains the requested record, restore history
    or synchronize it from current.

    If history contains the requested record and current is
    missing or older, restore current.

    A newer current record is never replaced by an older one.

    Returns:
        True if the requested historical record exists and
        current storage is consistent with it.
        False if the requested record cannot be recovered.
    """

    _validate_date(record_date)

    current_record = get_current_record(entity_id)
    history_record = get_history_record(entity_id, record_date)

    if current_record is not None:
        current_date = current_record["date"]

        if current_date == record_date:
            if current_record != history_record:
                _update_history(current_record)

            return True

        if current_date > record_date:
            # Current already contains a newer quotation.
            # The requested historical record must exist in history.
            return history_record is not None

    if history_record is None:
        return False

    # Current is missing or older than the requested record.
    _update_current(history_record)

    restored_record = get_current_record(entity_id, record_date)

    return restored_record is not None


def save_quote(entity: dict, quote: dict) -> None:
    """
    Save a quotation in historical and current storage.

    The caller must validate the quotation before calling this function.
    """

    record = _build_record(entity, quote)

    _update_history(record)
    _update_current(record)
