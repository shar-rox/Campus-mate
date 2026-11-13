"""Offline query matching for CampusMate's structured JSON records."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from utils.data_loader import all_records

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a", "about", "an", "and", "are", "at", "can", "do", "does", "for", "from",
    "get", "give", "help", "how", "i", "in", "is", "it", "me", "my", "of", "on",
    "please", "the", "there", "to", "what", "when", "where", "which", "who", "with",
    "would", "you", "your", "tell", "show", "find", "list", "all", "campus", "college",
    "available", "please", "now", "today", "currently", "right",
}
CATEGORY_KEYWORDS = {
    "classrooms": {"classroom", "classrooms", "room", "rooms", "lecture", "lecturehall"},
    "labs": {"lab", "labs", "laboratory", "laboratories", "computerlab", "researchlab"},
    "events": {"event", "events", "fest", "festival", "seminar", "workshop", "showcase", "today"},
    "facilities": {
        "facility", "facilities", "library", "canteen", "cafeteria", "dining", "auditorium",
        "gym", "sports", "clinic", "health", "printing", "photocopy", "courtyard",
    },
    "services": {
        "service", "services", "bonafide", "bona", "certificate", "certificates", "hostel",
        "transport", "fee", "fees", "receipt", "id", "transcript", "scholarship", "pass",
        "hall", "ticket", "exam", "maintenance",
    },
    "contacts": {"contact", "contacts", "phone", "email", "call", "person", "desk", "incharge"},
}
NAVIGATION_PHRASES = (
    "how do i reach", "how can i reach", "directions to", "how do i get to",
    "how can i get to", "way to", "navigate to", "route to", "take me to",
)
LIST_PHRASES = (
    "show", "list", "all ", "what facilities are available", "what services are available",
    "available labs", "available computer labs", "what events are happening",
)


def normalize(text: str) -> str:
    return " ".join(TOKEN_RE.findall(str(text).casefold()))


def query_tokens(text: str) -> list[str]:
    return [token for token in normalize(text).split() if token not in STOP_WORDS]


def detect_category(query: str) -> str | None:
    cleaned = normalize(query)
    compact = cleaned.replace(" ", "")

    if any(phrase in query.casefold() for phrase in NAVIGATION_PHRASES):
        return "navigation"
    if any(term in cleaned for term in ("who do i contact", "who should i contact", "phone", "email", "contact for", "call for")):
        return "contacts"

    raw_tokens = set(cleaned.split())
    compact_aliases = {
        "classrooms": {"classroom", "classrooms", "room", "rooms", "lecture"},
        "labs": {"lab", "labs", "laboratory", "laboratories"},
        "events": {"event", "events", "fest", "festival", "seminar", "workshop", "showcase"},
        "facilities": {"facility", "facilities", "library", "canteen", "cafeteria", "dining", "auditorium", "gym", "sports", "clinic", "health", "printing"},
        "services": {"service", "services", "bonafide", "certificate", "certificates", "hostel", "transport", "fee", "fees", "receipt", "transcript", "scholarship", "pass", "ticket", "exam", "maintenance"},
        "contacts": {"contact", "contacts", "phone", "email", "call", "person", "desk"},
    }

    if "who" in raw_tokens and ("contact" in raw_tokens or "call" in raw_tokens):
        return "contacts"
    for category in ("classrooms", "labs", "events", "facilities", "services", "contacts"):
        if raw_tokens.intersection(compact_aliases[category]):
            return category
        if any(phrase.replace(" ", "") in compact for phrase in CATEGORY_KEYWORDS[category] if len(phrase) > 5):
            return category
    return None


def _text_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [part for nested in value.values() for part in _text_values(nested)]
    if isinstance(value, (list, tuple, set)):
        return [part for nested in value for part in _text_values(nested)]
    if value is None:
        return []
    return [str(value)]


def _record_search_text(hit: dict[str, Any]) -> str:
    return normalize(" ".join(_text_values(hit["record"]) + [hit["category"]]))


def _token_score(token: str, record_tokens: set[str]) -> float:
    if token in record_tokens:
        return 1.0
    if len(token) < 4:
        return 0.0
    best = max((SequenceMatcher(None, token, candidate).ratio() for candidate in record_tokens), default=0.0)
    return 0.55 if best >= 0.84 else 0.0


def search_records(
    query: str,
    data: dict[str, Any],
    category: str | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Return ranked hits using category, field-token overlap, and small fuzzy recovery."""
    detected = category or detect_category(query)
    candidates = all_records(data)
    if detected and detected != "navigation":
        candidates = [hit for hit in candidates if hit["category"] == detected]

    tokens = query_tokens(query)
    ranked: list[dict[str, Any]] = []
    for hit in candidates:
        search_text = _record_search_text(hit)
        record_tokens = set(search_text.split())
        score = sum(_token_score(token, record_tokens) for token in tokens)
        name = normalize(hit["record"].get("name", ""))
        aliases = normalize(" ".join(_text_values(hit["record"].get("aliases", []))))
        identifier = normalize(hit["record"].get("id", ""))
        cleaned_query = normalize(query)
        query_entity = " ".join(tokens)
        if cleaned_query and cleaned_query in search_text:
            score += 1.3
        if name and name in cleaned_query:
            score += 2.0
        if query_entity and query_entity in aliases:
            score += 2.0
        elif query_entity and query_entity in name:
            score += 2.0
        elif aliases:
            alias_tokens = set(aliases.split())
            score += 0.45 * len(set(tokens).intersection(alias_tokens))
        score += 0.35 * len(set(tokens).intersection(set(name.split())))
        if identifier and identifier in cleaned_query.replace(" ", ""):
            score += 2.5
        if detected == hit["category"]:
            score += 0.25
        if score > 0:
            ranked.append({**hit, "score": score})

    ranked.sort(key=lambda hit: (hit["score"], hit["record"].get("name", "")), reverse=True)
    return ranked[:limit]


def is_current_availability_query(query: str) -> bool:
    cleaned = normalize(query)
    compact = cleaned.replace(" ", "")
    has_status = any(word in cleaned.split() for word in ("free", "vacant"))
    has_live_phrase = any(phrase in cleaned for phrase in ("available now", "available right now", "currently available", "open now", "open right now", "currently open", "at the moment"))
    question_form = cleaned.startswith(("is ", "are ", "can i use ")) and "available" in cleaned.split()
    return has_status or has_live_phrase or question_form or "available now" in compact


def is_listing_query(query: str) -> bool:
    cleaned = normalize(query)
    if is_current_availability_query(query):
        return False
    return any(phrase in cleaned for phrase in LIST_PHRASES) or cleaned.startswith(("list ", "show "))


def mentions_today(query: str) -> bool:
    return "today" in normalize(query).split()
