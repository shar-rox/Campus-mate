"""Turn matched local records into concise, source-labelled answers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from utils.data_loader import CATEGORY_LABELS
from utils.search_engine import (
    detect_category,
    is_current_availability_query,
    is_listing_query,
    mentions_today,
    query_tokens,
    search_records,
)

FALLBACK = (
    "I couldn't find that in this demo's campus data. I can help with classrooms, labs, events, "
    "facilities, student services, contacts, and basic campus directions. Try asking about the "
    "AI Lab, today's events, library hours, a bonafide certificate, or a campus office contact."
)


def _event_date(record: dict[str, Any]) -> date | None:
    try:
        return datetime.strptime(record.get("date", ""), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _listing_records(query: str, data: dict[str, Any], category: str) -> list[dict[str, Any]]:
    hits = search_records(query, data, category=category, limit=50)
    meaningful = set(query_tokens(query))
    if category == "labs" and "computer" in meaningful:
        hits = [
            hit for hit in hits
            if "computer" in " ".join(
                [hit["record"].get("name", ""), *hit["record"].get("aliases", [])]
            ).casefold()
        ]
    removable = {
        "classroom", "classrooms", "room", "rooms", "lab", "labs", "laboratory", "laboratories",
        "event", "events", "facility", "facilities", "service", "services", "contact", "contacts",
        "available", "campus", "today", "list", "show", "all",
    }
    specific = meaningful - removable
    if specific:
        filtered = [hit for hit in hits if hit["score"] >= 0.95 + min(len(specific), 2) * 0.65]
        if filtered:
            hits = filtered
    return hits


def answer_question(
    query: str,
    data: dict[str, Any],
    today: date | None = None,
) -> dict[str, Any]:
    """Return an answer object whose factual content is sourced from the local JSON."""
    cleaned = " ".join((query or "").split())
    if not cleaned:
        return {
            "summary": "Type a question about campus information to get started.",
            "category": "Help",
            "source": "campus_data.json",
            "records": [],
            "fallback": True,
        }

    current_day = today or date.today()
    category = detect_category(cleaned)

    if category == "events" and mentions_today(cleaned):
        events = [
            {"category": "events", "record": record, "score": 1.0}
            for record in data.get("events", [])
            if _event_date(record) == current_day
        ]
        label = current_day.strftime("%B %-d, %Y")
        summary = (
            f"Events listed for {label} in the fictional demo dataset."
            if events
            else f"No events are listed for {label} in the fictional demo dataset."
        )
        return {
            "summary": summary,
            "category": CATEGORY_LABELS["events"],
            "source": "campus_data.json",
            "records": events,
            "fallback": False,
        }

    if category in {"classrooms", "labs"} and is_current_availability_query(cleaned):
        hits = search_records(cleaned, data, category=category, limit=3)
        top_score = hits[0]["score"] if hits else 0
        records = [
            {"category": hit["category"], "record": hit["record"], "score": hit["score"]}
            for hit in hits
            if top_score > 0 and hit["score"] >= max(0.7, top_score - 0.45)
        ]
        label = "classroom" if category == "classrooms" else "lab"
        summary = (
            f"Live {label} availability is not connected in this prototype, so I can't confirm what is free right now. "
            "The related record below provides the location and the campus office to ask."
        )
        return {
            "summary": summary,
            "category": CATEGORY_LABELS[category],
            "source": "campus_data.json",
            "records": records,
            "fallback": False,
        }

    if category and category != "navigation" and is_listing_query(cleaned):
        hits = _listing_records(cleaned, data, category)
        records = [
            {"category": hit["category"], "record": hit["record"], "score": hit["score"]}
            for hit in hits
        ]
        if records:
            category_label = CATEGORY_LABELS[category]
            if category == "labs" and "available" in cleaned.casefold():
                summary = "Here are the labs listed in the demo dataset. Live lab availability is not tracked."
            else:
                summary = f"Here are the {category_label.casefold()} recorded in the fictional campus dataset."
            return {
                "summary": summary,
                "category": category_label,
                "source": "campus_data.json",
                "records": records,
                "fallback": False,
            }

    hits = search_records(cleaned, data, category=category, limit=5)
    if not hits or hits[0]["score"] < 0.8:
        return {
            "summary": FALLBACK,
            "category": "Not found",
            "source": "campus_data.json",
            "records": [],
            "fallback": True,
        }

    best = hits[0]["score"]
    selected = [hit for hit in hits if hit["score"] >= max(0.8, best - 0.45)][:2]
    records = [
        {"category": hit["category"], "record": hit["record"], "score": hit["score"]}
        for hit in selected
    ]
    selected_name = records[0]["record"].get("name", "the campus record")
    summary = f"Here's the information recorded for {selected_name}."
    response_category = CATEGORY_LABELS.get(records[0]["category"], "Campus information")

    return {
        "summary": summary,
        "category": response_category,
        "source": "campus_data.json",
        "records": records,
        "fallback": False,
    }


def record_details(hit: dict[str, Any]) -> list[tuple[str, Any]]:
    """Select relevant fields for a UI card without inventing data."""
    category = hit["category"]
    record = hit["record"]

    if category == "classrooms":
        fields = [
            ("Location", " · ".join(value for value in [record.get("building"), record.get("floor"), f"Room {record.get('room')}" if record.get("room") else None, record.get("nearby_landmark")] if value)),
            ("Capacity", f"{record.get('capacity')} students" if record.get("capacity") else None),
            ("Facilities", record.get("facilities")),
            ("Hours", record.get("timings")),
            ("Timetable", record.get("timetable")),
            ("Contact", record.get("contact")),
        ]
    elif category == "labs":
        fields = [
            ("Location", " · ".join(value for value in [record.get("building"), record.get("floor"), f"Room {record.get('room')}" if record.get("room") else None, record.get("nearby_landmark")] if value)),
            ("Capacity", f"{record.get('capacity')} students" if record.get("capacity") else None),
            ("Installed systems", f"{record.get('installed_systems')}" if record.get("installed_systems") is not None else None),
            ("Hours", record.get("timings")),
            ("Availability", record.get("availability_status")),
            ("Booking", record.get("booking")),
            ("Contact", record.get("contact")),
        ]
    elif category == "events":
        try:
            event_day = datetime.strptime(record.get("date", ""), "%Y-%m-%d").strftime("%B %-d, %Y")
        except (TypeError, ValueError):
            event_day = record.get("date")
        fields = [
            ("Date", event_day),
            ("Time", record.get("time")),
            ("Venue", record.get("venue")),
            ("Organizer", record.get("organizer")),
            ("About", record.get("description")),
            ("Registration", record.get("registration")),
        ]
    elif category == "facilities":
        fields = [
            ("Location", " · ".join(value for value in [record.get("location"), record.get("nearby_landmark")] if value)),
            ("Hours", record.get("timings")),
            ("Services", record.get("services")),
            ("Contact", record.get("contact")),
        ]
    elif category == "services":
        fields = [
            ("Office", record.get("office")),
            ("Location", record.get("location")),
            ("Steps", record.get("steps")),
            ("Documents", record.get("documents")),
            ("Hours", record.get("timings")),
            ("Contact", record.get("contact")),
            ("Note", record.get("note")),
        ]
    else:
        fields = [
            ("Department", record.get("department")),
            ("Contact", record.get("person")),
            ("Role", record.get("role")),
            ("Topics", record.get("topics")),
            ("Office", record.get("office")),
            ("Hours", record.get("timings")),
            ("Phone", record.get("phone")),
            ("Email", record.get("email")),
        ]

    return [(label, value) for label, value in fields if value not in (None, "", [])]
