"""Load and validate the fictional CampusMate knowledge base."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).resolve().parents[1] / "campus_data.json"
CATEGORY_COUNTS = {
    "classrooms": 8,
    "labs": 6,
    "events": 6,
    "facilities": 6,
    "services": 8,
    "contacts": 5,
}
CATEGORY_LABELS = {
    "classrooms": "Classrooms",
    "labs": "Labs",
    "events": "Events",
    "facilities": "Facilities",
    "services": "Student services",
    "contacts": "Contacts",
}


class CampusDataError(ValueError):
    """Raised when the local demo data is unreadable or malformed."""


def validate_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise CampusDataError("The knowledge base must be a JSON object.")

    for category, expected_count in CATEGORY_COUNTS.items():
        records = data.get(category)
        if not isinstance(records, list):
            raise CampusDataError(f"Knowledge base category '{category}' must be a list.")
        if len(records) != expected_count:
            raise CampusDataError(
                f"Expected {expected_count} {category} records; found {len(records)}."
            )
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict) or not record.get("id") or not record.get("name"):
                raise CampusDataError(
                    f"Record {index} in '{category}' needs an id and a name."
                )

    return data


def load_campus_data(path: str | Path = DATA_FILE) -> dict[str, Any]:
    """Read the knowledge base from disk, with a useful local error message."""
    data_path = Path(path)
    try:
        with data_path.open("r", encoding="utf-8") as data_file:
            return validate_data(json.load(data_file))
    except FileNotFoundError as exc:
        raise CampusDataError(f"Knowledge base file was not found: {data_path.name}") from exc
    except json.JSONDecodeError as exc:
        raise CampusDataError(
            f"Knowledge base JSON is invalid near line {exc.lineno}, column {exc.colno}."
        ) from exc


def total_records(data: dict[str, Any]) -> int:
    return sum(len(data.get(category, [])) for category in CATEGORY_COUNTS)


def all_records(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return records paired with their source category; source data is not mutated."""
    return [
        {"category": category, "record": record}
        for category in CATEGORY_COUNTS
        for record in data.get(category, [])
    ]
