"""CampusMate: an offline-first Streamlit campus information assistant."""

from __future__ import annotations

import html
import time
from pathlib import Path
from typing import Any

import streamlit as st

from utils.data_loader import CATEGORY_COUNTS, CATEGORY_LABELS, CampusDataError, load_campus_data, total_records
from utils.response_generator import answer_question, record_details

ROOT = Path(__file__).resolve().parent
STYLE_FILE = ROOT / "assets" / "theme.css"
MARK_FILE = ROOT / "assets" / "campusmate-mark.svg"
QUICK_ACTIONS = [
    ("Find a classroom", "Where is Room C-204?"),
    ("Lab availability", "Is the AI Lab available now?"),
    ("Today's events", "What events are happening today?"),
    ("Library timings", "When does the library close?"),
    ("Campus services", "What services are available?"),
    ("Important contacts", "Show important campus contacts."),
]

st.set_page_config(
    page_title="CampusMate | Alderwick College",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="auto",
)


def inject_styles() -> None:
    try:
        css = STYLE_FILE.read_text(encoding="utf-8")
    except OSError:
        css = ""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def safe_text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(safe_text(item) for item in value)
    return html.escape(str(value), quote=True)


def answer_card_markup(answer: dict[str, Any]) -> str:
    summary = safe_text(answer.get("summary", ""))
    category = safe_text(answer.get("category", "Campus information"))
    source = safe_text(answer.get("source", "campus_data.json"))
    sections: list[str] = []

    for hit in answer.get("records", []):
        record = hit.get("record", {})
        name = safe_text(record.get("name", "Campus record"))
        rows: list[str] = []
        for label, value in record_details(hit):
            if isinstance(value, (list, tuple)):
                display = "<ul>" + "".join(f"<li>{safe_text(item)}</li>" for item in value) + "</ul>"
            else:
                display = safe_text(value)
                if label in {"Contact", "Email"} and "@alderwick.example" in str(value):
                    email = html.escape(str(value), quote=True)
                    display = f'<a href="mailto:{email}">{email}</a>'
            rows.append(
                '<div class="fact-row"><span class="fact-label">'
                f"{safe_text(label)}</span><span class=\"fact-value\">{display}</span></div>"
            )
        sections.append(
            '<section class="record-card"><div class="record-heading">'
            f"<h3>{name}</h3><span class=\"record-kind\">{safe_text(CATEGORY_LABELS.get(hit.get('category'), 'Campus information'))}</span>"
            f"</div>{''.join(rows)}</section>"
        )

    return (
        '<div class="answer-panel">'
        f'<div class="answer-topline"><span class="answer-category">{category}</span>'
        f'<span class="answer-source">Source: {source}</span></div>'
        f'<p class="answer-summary">{summary}</p>{"".join(sections)}'
        "</div>"
    )


def navigate(page: str, question: str | None = None) -> None:
    st.session_state["view"] = page
    if question:
        st.session_state["pending_query"] = question


def render_sidebar(data: dict[str, Any]) -> str:
    with st.sidebar:
        if MARK_FILE.exists():
            st.image(str(MARK_FILE), width=48)
        st.markdown('<div class="sidebar-wordmark">CampusMate</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-subtitle">ALDERWICK COLLEGE<br>INFORMATION DESK</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-rule"></div>', unsafe_allow_html=True)

        pages = [
            ("Assistant", "assistant"),
            ("About this demo", "about"),
            ("Terms of Service", "terms"),
            ("Privacy Policy", "privacy"),
        ]
        for label, page in pages:
            is_active = st.session_state.get("view", "assistant") == page
            if st.button(label, key=f"nav_{page}", type="primary" if is_active else "secondary", use_container_width=True):
                navigate(page)
                st.rerun()

        st.markdown('<div class="sidebar-rule"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-kicker">SUPPORTED TOPICS</div>', unsafe_allow_html=True)
        for label in ["Classrooms", "Labs", "Events", "Facilities", "Student services", "Contacts", "Directions"]:
            st.markdown(f'<div class="topic-line">{html.escape(label)}</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-rule"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-kicker">TRY A QUESTION</div>', unsafe_allow_html=True)
        sidebar_examples = [
            ("Find the AI Lab", "Where is the AI Lab?"),
            ("Library hours", "When does the library close?"),
            ("Get a bonafide", "How do I apply for a bonafide certificate?"),
        ]
        for label, question in sidebar_examples:
            if st.button(label, key=f"sample_{label}", use_container_width=True):
                navigate("assistant", question)
                st.rerun()

        st.markdown('<div class="sidebar-note">Fictional sample data only. This assistant does not connect to live campus systems.</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="sidebar-count">{total_records(data)} sample records in the local knowledge base</div>',
            unsafe_allow_html=True,
        )
    return st.session_state.get("view", "assistant")


def render_mobile_brand() -> None:
    with st.container(key="mobile_brand"):
        mark_col, text_col = st.columns([0.18, 1], gap="small", vertical_alignment="center")
        with mark_col:
            if MARK_FILE.exists():
                st.image(str(MARK_FILE), width=40)
        with text_col:
            st.markdown(
                '<div class="mobile-wordmark">CampusMate</div>'
                '<div class="mobile-college">ALDERWICK COLLEGE · INFORMATION DESK</div>',
                unsafe_allow_html=True,
            )


def render_mobile_navigation() -> None:
    pages = [
        ("Chat", "assistant"),
        ("About", "about"),
        ("Terms", "terms"),
        ("Privacy", "privacy"),
    ]
    with st.container(key="mobile_nav"):
        cols = st.columns(len(pages), gap="small")
        for col, (label, page) in zip(cols, pages):
            with col:
                active = st.session_state.get("view", "assistant") == page
                if st.button(label, key=f"mobile_nav_{page}", type="primary" if active else "secondary", use_container_width=True):
                    navigate(page)
                    st.rerun()


def render_skeleton() -> None:
    st.markdown(
        '<div class="answer-panel loading-panel" role="status" aria-label="Finding campus information">'
        '<div class="skeleton-line skeleton-short"></div><div class="skeleton-line skeleton-long"></div>'
        '<div class="skeleton-line skeleton-medium"></div><div class="skeleton-line skeleton-long"></div></div>',
        unsafe_allow_html=True,
    )


def render_conversation(data: dict[str, Any]) -> None:
    messages = st.session_state.setdefault("messages", [])
    for item in messages:
        with st.chat_message(item["role"]):
            if item["role"] == "assistant":
                st.markdown('<div class="speaker-label">CAMPUSMATE</div>', unsafe_allow_html=True)
                st.markdown(answer_card_markup(item["answer"]), unsafe_allow_html=True)
            else:
                st.markdown(item["content"])

    pending = st.session_state.pop("pending_query", None)
    if pending and pending.strip():
        messages.append({"role": "user", "content": pending.strip()})
        with st.chat_message("user"):
            st.markdown(pending.strip())
        with st.chat_message("assistant"):
            st.markdown('<div class="speaker-label">CAMPUSMATE</div>', unsafe_allow_html=True)
            placeholder = st.empty()
            placeholder.markdown(
                '<div class="answer-panel loading-panel" role="status" aria-label="Finding campus information">'
                '<span class="loading-label">Checking the campus guide</span>'
                '<div class="skeleton-line skeleton-short"></div><div class="skeleton-line skeleton-long"></div>'
                '<div class="skeleton-line skeleton-medium"></div></div>',
                unsafe_allow_html=True,
            )
            time.sleep(0.12)
            try:
                response = answer_question(pending, data)
            except Exception:
                response = {
                    "summary": "I could not read the local campus guide. Check that campus_data.json is valid and try again.",
                    "category": "Local data issue",
                    "source": "campus_data.json",
                    "records": [],
                    "fallback": True,
                }
            placeholder.markdown(answer_card_markup(response), unsafe_allow_html=True)
        messages.append({"role": "assistant", "answer": response})


def render_quick_actions() -> None:
    st.markdown('<div class="section-kicker">QUICK QUESTIONS</div>', unsafe_allow_html=True)
    for row in range(2):
        cols = st.columns(3, gap="small")
        for col_index, col in enumerate(cols):
            label, question = QUICK_ACTIONS[row * 3 + col_index]
            with col:
                if st.button(label, key=f"quick_{row}_{col_index}", use_container_width=True):
                    navigate("assistant", question)
                    st.rerun()


def render_assistant(data: dict[str, Any]) -> None:
    st.markdown('<div class="page-kicker">CAMPUS INFORMATION, WITHOUT THE RUNAROUND</div>', unsafe_allow_html=True)
    title_col, note_col = st.columns([2.2, 1], vertical_alignment="bottom")
    with title_col:
        st.markdown('<h1 class="page-title">What are you looking for?</h1>', unsafe_allow_html=True)
    with note_col:
        st.markdown('<div class="sample-note"><span class="sample-dot"></span> Demo dataset<br>Not live campus data</div>', unsafe_allow_html=True)

    st.markdown('<p class="page-intro">Ask a question about rooms, labs, campus life, or student services. Answers come from the local Alderwick sample guide.</p>', unsafe_allow_html=True)
    render_quick_actions()

    messages = st.session_state.setdefault("messages", [])
    if not messages and not st.session_state.get("pending_query"):
        st.markdown(
            '<div class="empty-state"><div class="empty-index">01 / ASK THE CAMPUS GUIDE</div>'
            '<h2>Start with a place, a service, or a question.</h2>'
            '<p>For example: “Where is Room C-204?” or “How do I request a bonafide certificate?”</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="conversation-label">CONVERSATION</div>', unsafe_allow_html=True)
    render_conversation(data)

    if st.session_state.get("messages"):
        control_col, _ = st.columns([1, 4])
        with control_col:
            if st.button("New conversation", key="clear_conversation", use_container_width=True):
                st.session_state["messages"] = []
                st.session_state.pop("pending_query", None)
                st.rerun()

    with st.form("ask_campusmate", clear_on_submit=True, border=False):
        input_col, send_col = st.columns([5, 1], vertical_alignment="bottom")
        with input_col:
            prompt = st.text_input(
                "Ask a campus question",
                placeholder="Ask about a classroom, lab, event, facility, or student service...",
                label_visibility="collapsed",
                key="campus_question",
            )
        with send_col:
            submitted = st.form_submit_button("Send", type="primary", use_container_width=True)
        if submitted:
            if prompt and prompt.strip():
                st.session_state["pending_query"] = prompt.strip()
            st.rerun()
    st.markdown('<div class="input-footnote">Enter a question. The demo uses fictional local data and cannot confirm live schedules or availability.</div>', unsafe_allow_html=True)


def render_about(data: dict[str, Any]) -> None:
    st.markdown('<div class="page-kicker">ABOUT THE PROJECT</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Campus information, made easier to find.</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="reading-panel"><p class="lead-copy">CampusMate is an offline-first campus assistant prototype. It searches a small, inspectable JSON guide and shows the source category for each answer.</p>'
        '<p>This Alderwick College dataset is fictional. It does not connect to a real school, timetable, booking system, event feed, student portal, or account service.</p>'
        '<h2>What it can answer</h2><p>Classroom locations, lab details, listed events, facility hours, student-service steps, department contacts, and basic directions when those details exist in the local guide.</p>'
        '<h2>What it cannot confirm</h2><p>Live room or lab availability, up-to-date event changes, current account balances, admissions fees, booking status, or facts that are absent from the demo dataset.</p>'
        '<h2>How matching works</h2><p>Questions are normalized and matched locally with category keywords, token overlap, and fuzzy word matching. The response formatter uses retrieved JSON fields only.</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-kicker">SAMPLE QUESTIONS</div>', unsafe_allow_html=True)
    for row in range(2):
        cols = st.columns(3)
        for index, col in enumerate(cols):
            label, question = QUICK_ACTIONS[row * 3 + index]
            with col:
                if st.button(label, key=f"about_{row}_{index}", use_container_width=True):
                    navigate("assistant", question)
                    st.rerun()


def render_legal_page(page: str) -> None:
    if page == "terms":
        st.markdown('<div class="page-kicker">CAMPUSMATE DEMO</div>', unsafe_allow_html=True)
        st.markdown('<h1 class="page-title">Terms of Service</h1>', unsafe_allow_html=True)
        st.markdown(
            '<div class="reading-panel"><p class="lead-copy">This prototype is provided for demonstration and educational use.</p>'
            '<h2>Demo information</h2><p>Campus names, people, contact details, events, schedules, and procedures shown here are fictional sample data. Do not rely on them for real campus decisions or official advice.</p>'
            '<h2>Availability and accuracy</h2><p>CampusMate searches its bundled JSON data only. It does not connect to a live timetable, room booking system, event feed, student account, or college office.</p>'
            '<h2>Use of the prototype</h2><p>Do not enter passwords, payment details, health information, or other sensitive personal information. This demo has no account or payment workflow.</p>'
            '<h2>Changes</h2><p>The prototype and its sample data may change as the demonstration is developed. This page describes the demo only and is not a substitute for a real institution’s terms.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="page-kicker">CAMPUSMATE DEMO</div>', unsafe_allow_html=True)
        st.markdown('<h1 class="page-title">Privacy Policy</h1>', unsafe_allow_html=True)
        st.markdown(
            '<div class="reading-panel"><p class="lead-copy">This prototype is designed to answer questions locally from its bundled fictional campus guide.</p>'
            '<h2>Questions and chat history</h2><p>Your question is processed by the local application logic. Conversation history is held in the active Streamlit session and is not written to the bundled JSON file or a CampusMate database. It is cleared when the session ends or when you choose New conversation.</p>'
            '<h2>Data collection</h2><p>The prototype does not request an account, password, location, payment information, or other personal details. Please do not include sensitive personal information in a question.</p>'
            '<h2>Demo records</h2><p>The campus records are fictional and are shipped with the application. They are not personal information about real students or staff.</p>'
            '<h2>Scope</h2><p>This page describes the current demonstration build. It is not a privacy notice for any college or institution.</p></div>',
            unsafe_allow_html=True,
        )


def main() -> None:
    inject_styles()
    if "view" not in st.session_state:
        st.session_state["view"] = "assistant"
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    try:
        data = load_campus_data()
    except CampusDataError as exc:
        st.error(f"CampusMate could not load its local data: {exc}")
        st.caption("Check campus_data.json and refresh the app.")
        return

    view = render_sidebar(data)
    render_mobile_brand()
    render_mobile_navigation()
    view = st.session_state.get("view", view)
    if view == "assistant":
        render_assistant(data)
    elif view == "about":
        render_about(data)
    elif view in {"terms", "privacy"}:
        render_legal_page(view)
    st.markdown('<div class="page-footer">CampusMate · Fictional demonstration data · No live campus connection</div>', unsafe_allow_html=True)


main()
