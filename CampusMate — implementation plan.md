# CampusMate — implementation plan

## Scope and build approach

Build the supplied CampusMate prototype as a single-page Python/Streamlit web application, preserving the attachment's requested stack and offline-first behavior. It will run on the configured web preview port, serve from `0.0.0.0`, and require no API key, external database, or network connection for assistant answers. The campus data is fictional demonstration content, not live institutional information.

The application will use a structured `campus_data.json` knowledge base and modular Python utilities for loading, normalization, intent/category detection, keyword scoring, fuzzy matching, grounded response formatting, and fallback/error handling. Query results must be selected from the JSON records only. The optional LLM integration is not required for the complete working prototype; if added later, it must be opt-in, grounded in retrieved records, and must not disable offline behavior. No live timetable, room availability, event feed, fees, or booking status will be implied where the sample dataset has no such fact.

The dataset will contain 39 fictional records: 8 classrooms, 6 labs, 6 events, 6 facilities, 8 student services, and 5 department/contact records. Event dates will be explicit sample data, and "today" means the current date against that dataset. Queries such as "which rooms are free now" will clearly explain that real-time schedules are not included, rather than inventing availability. Quick prompts, session chat history, category-aware answer cards, supported-category fallback, and error handling will be implemented.

The project will include the requested setup/run instructions, dependency file, demo script, and future-scope notes. The interface will also include accessible Terms of Service and Privacy Policy views because the user explicitly requires them; their copy will describe this demo accurately, including session-only chat history and fictional data, and will not claim legal advice or institutional authority.

## Project structure

```text
campmate/
├── .gitignore                     # Excludes local Python caches and virtual environments
├── app.config.ts                  # Project-level logo metadata for the bespoke campus mark
├── pyrightconfig.json             # Project-root and virtual-environment Python diagnostics
├── app.py                         # Streamlit page shell, chat state and interactions
├── run.py                         # Local HTTP bridge: route manifest at root and proxy to Streamlit
├── campus_data.json               # Fictional campus facts; sole source for assistant answers
├── requirements.txt               # Pinned/runtime dependencies (primarily Streamlit)
├── README.md                       # Setup, run, architecture, limitations and demo use
├── plan.md                         # This approved implementation/design plan
├── TODO.md                         # Outcome-based implementation status after plan approval
├── DEMO_SCRIPT.md                  # Short presentation walkthrough and demo prompts
├── public/manus-routes.json        # Declares the app's single page route for Preview
├── utils/
│   ├── __init__.py
│   ├── data_loader.py              # Validates and loads the local JSON knowledge base
│   ├── search_engine.py            # Preprocessing, intent detection, keyword/fuzzy ranking
│   └── response_generator.py       # Grounded category-specific answer formatting and fallback
└── assets/
    └── campusmate-mark.svg         # Custom simple academic mark; no generic icon-library dependency
```

There is no separate application API or persistent database: `run.py` exposes the required single-page route manifest at `/manus-routes.json` and transparently proxies HTTP and WebSocket traffic to the local Streamlit process on an internal port. Streamlit serves the complete UI and Python query logic, while the JSON file is the local data source. Chat history remains in Streamlit session state. The single-page route contains internal navigation for the app, About, Terms of Service, and Privacy Policy. The bridge disables Streamlit's same-origin and XSRF checks only for this no-login, no-persistent-data local demo, allowing public Preview's reverse proxy/iframe to connect; it exposes no new application data endpoint beyond the manifest and proxied Streamlit app.

## Proposed design direction

The supplied brief asks for a clean, modern, student-friendly demonstration interface but does not name a visual style. Three distinct possibilities are: **Campus field guide/editorial**, a compact editorial directory with paper-like warm surfaces (**0.061**); **Contemporary institutional signage**, crisp wayfinding typography with disciplined deep-green and stone colors (**0.044**); **Library archive index**, restrained archival labeling, serif headlines, and catalog-like navigation (**0.083**). The user approved the Campus field guide/editorial direction.

- **Design movement:** Contemporary editorial field guide, borrowing the clarity of campus wayfinding and academic publications rather than a generic SaaS dashboard.
- **Core principles:** Information-first hierarchy; human-scale, calm composition; distinct but consistent record treatments; clear provenance and limitations.
- **Color philosophy:** Warm ivory/stone and ink provide comfortable contrast without an all-white page; deep evergreen and restrained ochre signal navigation and selected actions. No neon, rainbow, pastel, purple-black, or gradient treatments.
- **Layout paradigm:** A responsive two-part workspace on desktop: a narrow campus identity/navigation rail beside a spacious, transcript-led conversation. On small screens the rail becomes a compact top/header navigation and the chat remains the primary content. Information is presented in conversational answers and varied content rows, not generic bento grids or repeated feature-card rows.
- **Signature elements:** A custom, compact academic building/wayfinding mark; subtle catalog-style category labels; answer source/category labels that make the JSON grounding visible.
- **Interaction philosophy:** Direct and predictable: searchable natural-language questions, suggestion chips, keyboard submission, visible processing state, clear answer provenance, and a helpful unsupported-query fallback. No decorative motion; focus, disabled, loading, and error states are explicit.
- **Animation:** Minimal and purposeful only: a short, reduced-motion-aware response loading transition and subtle opacity change on page-state updates. No pointless arrows or broad hover animation system.
- **Typography system:** A locally available editorial serif stack (`Iowan Old Style`, `Palatino Linotype`, `Book Antiqua`, Georgia) for headlines and the native system sans-serif stack for interface/body text, avoiding external font downloads and the excluded overused font families. Keep an accessible size/line-height hierarchy.
- **Brand essence:** A dependable campus information desk for students and visitors, grounded in an inspectable local knowledge file; **clear, practical, welcoming**.
- **Brand voice:** Concise, specific, and honest about uncertainty. Example: “The AI Lab is in CS-301, on the third floor of the Computer Science Block.” “I don’t have live room schedules in this demo, so I can’t confirm what’s free right now.”
- **Wordmark & logo:** A simple bespoke line mark combining a campus entrance and a location/wayfinding cue, paired with the CampusMate wordmark; not an icon-library glyph.
- **Signature brand color:** Deep evergreen, used sparingly for primary actions and selected navigation.

## Explicit UI exclusions and constraints

The following user constraints are hard exclusions for the design and implementation: harsh gradients; generic Lucide icon usage; pure-white backgrounds everywhere; rainbow color schemes; excessive drop shadows; three identical feature cards in a row; emojis as interface elements; liquid-glass effects; excessive em dashes in website copy; overused Inter, Geist, or Space Grotesk typography; colored left-border accent stripes on every card; fake testimonials or fabricated social proof; generic bento-grid layouts; unnecessary terminal-window aesthetics; repetitive AI-generated copy patterns such as “It's not X, it's Y”; generic checkmark bullet lists; predictable three-tier pricing sections; static mockups instead of a real product demonstration; missing skeleton loading states; purple-and-black generic AI aesthetics; decorative radial orbs; unnecessary dot-grid backgrounds; sparkle icons and AI decoration; pointless animated arrows; missing Terms of Service; missing Privacy Policy; generic hover animations everywhere; neon colors; and basic pastel color schemes. The brief repeats the skeleton-loading prohibition; it is treated as one requirement. The assistant itself will be a real, interactive implementation, not a static mockup.

## Constraints and implementation decisions

- Python + Streamlit are retained from the supplied build brief. The custom CSS will handle responsive layout and restrained brand styling without changing the underlying interaction model.
- Matching is deterministic and local. Fuzzy matching will use Python standard-library facilities where practical; avoid heavyweight model/vector dependencies for the prototype.
- All sample people, office contacts, events, room capacities, dates, and policies are invented and labeled as demonstration data. No real school is represented.
- User messages must never cause an unsupported fact to be generated. The fallback will identify supported categories and offer example questions.
- No account/login, remote service, database, or external API is introduced. The knowledge base and the application remain usable offline after dependencies are installed.
- A lightweight status/loading treatment will be present for initial data loading and answer processing, and honor reduced-motion preferences.

## Approval gate

This is the approved implementation and design plan. The user approved the direction and supplied the strict exclusions listed above. The implementation proceeds with outcome-based `TODO.md`, registered Python/JSON diagnostics, the local route-manifest bridge, and the Streamlit application; verify the configured Preview port and resolve any actionable diagnostics before delivery.
