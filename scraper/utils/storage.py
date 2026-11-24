
import json
import os
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from scraper.config import (
    CURRENT_DATA_FILE,
    HISTORY_DIR,
    CURRENCY,
    PRICE_CURRENCY,
)


def _json_compatible(value):
    """Convert Decimal values into JSON-compatible numbers."""

    if isinstance(value, Decimal):
        return float(value)

    raise TypeError(
        f"Unsupported JSON data type: {type(value).__name__}"
    )


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
    """Read current quotation data or return its initial structure."""

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

    if not isinstance(data.get("entities"), list):
        raise ValueError("current.json must contain an entities list.")

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

    record = {
        "date": quote["date"],
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
            if item.get("id") == record["id"]
        ),
        None,
    )

    if existing_index is None:
        entities.append(record)

    else:
        existing_record = entities[existing_index]

        if record["date"] < existing_record.get("date", ""):
            return False

        entities[existing_index] = record

    data["updated_at"] = datetime.now().astimezone().isoformat()
    data["currency"] = CURRENCY
    data["price_currency"] = PRICE_CURRENCY

    _write_current_data(data)

    return True


def _read_history(path: Path) -> list[dict]:
    """Read all records from a JSONL history file."""

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

            records.append(record)

    return records


def _update_history(record: dict) -> None:
    """
    Insert or replace a historical record.

    Each entity can have only one record per date.
    """

    year = record["date"][:4]
    history_file = HISTORY_DIR / f"{year}.jsonl"

    records = _read_history(history_file)

    updated = False

    for index, existing in enumerate(records):

        if (
            existing.get("id") == record["id"]
            and existing.get("date") == record["date"]
        ):
            records[index] = record
            updated = True
            break

    if not updated:
        records.append(record)

    records.sort(
        key=lambda item: (
            item.get("date", ""),
            item.get("id", ""),
        )
    )

    content = "".join(
        json.dumps(
            item,
            ensure_ascii=False,
            default=_json_compatible,
        ) + "\n"
        for item in records
    )

    _atomic_write(history_file, content)


def save_quote(entity: dict, quote: dict) -> None:
    """
    Save a quotation in historical and current storage.

    The caller must validate the quotation before calling this function.
    """

    record = _build_record(entity, quote)

    _update_history(record)
    _update_current(record)
