"""Validate public exchange-rate files before a scraper workflow publishes them."""

import json
import math
import subprocess
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = ROOT / "frontend" / "data"
CURRENT_FILE = DATA_DIRECTORY / "current.json"


def _validate_record(record: object, source: str) -> dict:
    if not isinstance(record, dict):
        raise ValueError(f"{source}: each record must be a JSON object.")

    entity_id = record.get("id")
    record_date = record.get("date")
    if not isinstance(entity_id, str) or not entity_id.strip():
        raise ValueError(f"{source}: record has an invalid entity ID.")
    if not isinstance(record_date, str):
        raise ValueError(f"{source}: record has no valid date.")
    try:
        if date.fromisoformat(record_date).isoformat() != record_date:
            raise ValueError
    except ValueError as exc:
        raise ValueError(f"{source}: invalid date {record_date!r}.") from exc

    rate_fields = (
        ("official_rate",)
        if record.get("type") == "central_bank"
        else ("buy", "sell")
        if record.get("type") == "commercial_bank"
        else ()
    )
    if not rate_fields:
        raise ValueError(f"{source}: unsupported entity type.")
    for field in rate_fields:
        value = record.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{source}: {field} must be numeric.")
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{source}: {field} must be finite and positive.")
    return record


def _git_output(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _load_history(path: Path) -> list[dict]:
    records = []
    seen_dates = set()
    with path.open(encoding="utf-8") as history_file:
        for line_number, line in enumerate(history_file, start=1):
            if not line.strip():
                continue
            source = f"{path.relative_to(ROOT)}:{line_number}"
            try:
                raw_record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{source}: invalid JSONL record.") from exc
            record = _validate_record(raw_record, source)
            if record["id"] != path.stem:
                raise ValueError(f"{source}: entity ID does not match filename.")
            if record["date"] in seen_dates:
                raise ValueError(f"{source}: duplicate date for this entity.")
            seen_dates.add(record["date"])
            records.append(record)
    return records


def validate_public_data() -> None:
    """Validate current and historical data and ensure tracked history remains."""

    with CURRENT_FILE.open(encoding="utf-8") as current_file:
        current_data = json.load(current_file)
    if not isinstance(current_data, dict) or not isinstance(
        current_data.get("entities"), list
    ):
        raise ValueError("frontend/data/current.json must contain an entities list.")

    current_ids = set()
    for index, raw_record in enumerate(current_data["entities"]):
        record = _validate_record(raw_record, f"current.json:{index + 1}")
        if record["id"] in current_ids:
            raise ValueError(f"current.json: duplicate entity {record['id']}.")
        current_ids.add(record["id"])

    previous_current = json.loads(_git_output("show", "HEAD:frontend/data/current.json"))
    previous_ids = {record["id"] for record in previous_current["entities"]}
    if not previous_ids.issubset(current_ids):
        missing = ", ".join(sorted(previous_ids - current_ids))
        raise ValueError(f"current.json lost existing entities: {missing}.")

    tracked_history = _git_output(
        "ls-tree", "-r", "--name-only", "HEAD", "--", "frontend/data/history"
    ).splitlines()
    history_directory = DATA_DIRECTORY / "history"
    for relative_path in tracked_history:
        history_path = ROOT / relative_path
        if not history_path.is_file():
            raise ValueError(f"Existing history file was removed: {relative_path}.")
        previous_lines = _git_output("show", f"HEAD:{relative_path}").splitlines()
        previous_dates = {
            _validate_record(json.loads(line), relative_path)["date"]
            for line in previous_lines
            if line.strip()
        }
        current_records = _load_history(history_path)
        current_dates = {record["date"] for record in current_records}
        if not previous_dates.issubset(current_dates):
            missing = ", ".join(sorted(previous_dates - current_dates))
            raise ValueError(f"{relative_path} lost historical dates: {missing}.")

    for history_path in history_directory.glob("*/*.jsonl"):
        _load_history(history_path)


if __name__ == "__main__":
    validate_public_data()
    print("Public current and historical data validated successfully.")
