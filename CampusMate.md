# CampusMate

CampusMate is a working, offline-first campus information assistant prototype. It uses Streamlit for its chat UI and a fictional local JSON knowledge base for its answers. The sample institution is Alderwick College, created for demonstration only.

## Run locally

Python 3.10 or later is recommended.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
python run.py
```

Open the address printed by the app (normally `http://localhost:3000`). The bridge serves `GET /manus-routes.json` and proxies browser HTTP and WebSocket requests to the Streamlit process. To run the app directly without the bridge, use `streamlit run app.py`; the bridge is needed for the Manus Preview route manifest.

No API key, database, or external service is required for answers. Python packages must be installed before first use; after that, query matching and response generation use only local code and `campus_data.json`. Typography falls back to system fonts and does not need a font download.

## What is included

- `app.py`: Responsive Streamlit chat, session history, quick prompts, navigation, About, Terms of Service, and Privacy Policy.
- `app.config.ts`: Project-level logo metadata for the original campus mark.
- `run.py`: Small local HTTP/WebSocket bridge for the required route manifest and Streamlit preview.
- `campus_data.json`: 39 fictional records: 8 classrooms, 6 labs, 6 events, 6 facilities, 8 student services, and 5 department/contact records.
- `utils/data_loader.py`: Local JSON loading, count validation, and data integrity errors.
- `utils/search_engine.py`: Query cleanup, category recognition, keyword overlap, fuzzy matching, and query-intent helpers.
- `utils/response_generator.py`: Grounded answer selection, event-day filtering, category-specific fields, and safe fallback behavior.
- `assets/theme.css`: Responsive visual system; `assets/campusmate-mark.svg` is a small original project mark.
- `DEMO_SCRIPT.md`: Suggested short live demonstration.

## Grounding and limitations

All factual answer fields come from `campus_data.json`. The app does not connect to live campus timetables, room or lab bookings, event systems, payments, student records, or institution staff. When asked what is free now, it says live availability is not tracked and may show a related room/lab record. Event dates are fictional; “today” is matched against the server's current date and the sample dates. A missing fact receives a fallback that lists supported areas rather than a guessed answer.

Chat history is held in the active Streamlit session and disappears when the session ends or the user starts a new conversation. Do not enter sensitive information. The Terms of Service and Privacy Policy pages describe the prototype only and are not official legal notices for a real institution.

## Project structure

```text
campmate/
├── .gitignore
├── app.config.ts
├── pyrightconfig.json
├── app.py
├── run.py
├── campus_data.json
├── requirements.txt
├── README.md
├── plan.md
├── TODO.md
├── DEMO_SCRIPT.md
├── public/manus-routes.json
├── utils/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── search_engine.py
│   └── response_generator.py
└── assets/
    ├── campusmate-mark.svg
    └── theme.css
```

## Future improvements

A production system could connect approved campus records to a live timetable or room-booking system, import event notices and institutional documents, add multilingual and voice interaction, provide a map when a verified map source exists, and offer an admin-managed knowledge base with authentication. None of those live integrations are present in this demo.
