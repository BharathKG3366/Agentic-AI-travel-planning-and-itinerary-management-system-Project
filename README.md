# VoyageWise AI — Agentic Travel Planning & Itinerary Management

A beginner-friendly M.Tech. CSE mini-project that combines an explicit multi-agent workflow, external tool calling, constraint-based itinerary planning, local memory, human approval, and feedback-driven dynamic replanning. It supports flight search, Indian train route/fare discovery, destination places and weather forecasts.

> **Important:** This is a travel-search and planning prototype, not a ticketing platform. It does not book flights/trains/hotels or accept payment. Flight search requires a SerpApi key; train search requires a supported RapidAPI subscription/key. Weather and mapped-place queries use public endpoints. No result is replaced with a fabricated live fare if a provider is unavailable.

## What is included

- Responsive glossy-style Streamlit interface with switchable light/dark themes.
- Flight search using Google Flights results through SerpApi, with provider timestamp and comparison link.
- Indian train route search and optional indicative fare lookup through a third-party RapidAPI provider; station autocomplete is included.
- Weather forecast and geocoding through Open-Meteo.
- Destination point-of-interest lookup via OpenStreetMap Overpass.
- LangGraph workflow nodes for goal decomposition, research, transport tools, itinerary planning, validation and the human approval gate.
- Optional Gemini itinerary scheduling/replanning. A deterministic planner still works when no LLM key is configured.
- Constraint/budget validation with transparent, user-entered accommodation/food/local-transport estimates.
- Local SQLite memory for preferences, trip drafts and agent events.
- Human approval after initial generation and after every replan; local approval does not book anything.
- Replanning rules for rain/indoor alternatives, nature preferences, a slower pace, and an explicit new budget.
- JSON and CSV itinerary exports, automated offline tests and project documentation.

## Requirements

- Windows 10/11, macOS or Linux.
- Python 3.12 recommended (Python 3.13 may also work with current package versions).
- VS Code recommended, but not required.
- Internet connection for live/public provider queries.

## Quick start — Windows / VS Code

1. Extract the ZIP to a normal folder, for example `Documents\voyagewise_agentic_travel_planner`.
2. Open that folder in VS Code (**File → Open Folder**).
3. Open **Terminal → New Terminal** and run:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

   If the environment already exists, do not recreate it unnecessarily. If PowerShell blocks activation, select **Python: Create Environment → Venv** from the VS Code Command Palette and choose Python 3.12.

4. Open `.env` in VS Code. Add whichever keys you choose to configure. Keep secrets private; `.env` is in `.gitignore`.
5. Start the app:

   ```powershell
   streamlit run app.py
   ```

6. Streamlit opens a local browser tab. Theme can be changed using **⋮ → Settings → Theme → Light/Dark**.

## macOS / Linux quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

## Configure the integrations

Read [`docs/API_SETUP.md`](docs/API_SETUP.md) for provider links, credential names, testing and limitations.

- `SERPAPI_KEY`: flight offer search.
- `RAPIDAPI_KEY`: Indian Railways route/fare provider.
- `GEMINI_API_KEY`: optional AI-based schedule drafting and feedback replanning. Without it, the rule-based planner/replanner remains usable.
- Open-Meteo + OpenStreetMap: no API key in this prototype; subject to public service terms, usage limits and availability.

The default Gemini model is `gemini-3.8-flash`; verify current model availability and quota in Google AI Studio before relying on it. The free tier has limits and its data terms may differ from paid plans. Prefer synthetic travel examples and do not send sensitive personal data.

## Recommended first run

- Open **Plan a Trip** and create a short trip.
- Leave transport set to **None** if the flight/train provider keys are not configured.
- The app tries to fetch mapped attractions and forecast information, creates a draft itinerary, checks the cost estimates, stores a local trip record and pauses for approval.
- If destination data services fail, the app tells you and shows a generic flexible activity instead of inventing a named live attraction.
- Open **Transport Search** for flights (IATA codes such as BLR/DEL) or trains (station codes such as SBC/NDLS), and use a returned option in the itinerary if desired.
- Use **Run dynamic replanning** with requests like `rain is expected on Day 2`, `make the pace slower with fewer places`, `prioritize nature and viewpoints`, or `reduce the total budget to ₹20000`.
- Open **Trip Memory** to review saved drafts and preferences.

## Run tests

```powershell
python -m pytest -q
```

Tests are offline and do not need provider credentials. They test normalization, budget checks, constrained place names, and replanning rules. They do not establish that your own API credentials/quota work.

## Project layout

```text
voyagewise_agentic_travel_planner/
├── app.py                  # Streamlit UI and interaction
├── agents/
│   ├── workflow.py         # LangGraph supervisor workflow
│   ├── planner.py          # itinerary drafting, validation and replanning
│   └── memory.py           # SQLite preference/trip/event memory
├── providers/
│   ├── flights.py          # SerpApi Google Flights search
│   ├── railways.py         # RapidAPI Indian train route/fare connector
│   ├── weather.py          # Open-Meteo geocoding/forecast
│   └── places.py           # OpenStreetMap Overpass places
├── tests/                  # Offline unit tests
├── docs/                   # Requirements, architecture, API setup, evaluation
├── .streamlit/config.toml  # Light/dark palettes
├── .env.example             # Safe template; contains no real secrets
└── requirements.txt
```

## Data quality and safety boundaries

- A “fresh provider response” means the app just requested data from a provider; it does not guarantee a fare will still be available at checkout.
- The train connector returns route/schedule information and can return an indicative fare. It does **not** check seat inventory/PNR or purchase tickets.
- OpenStreetMap is community-mapped data. It does not provide guaranteed opening hours, temporary closures, ticket pricing or accessibility status.
- Forecasts are model predictions and have a limited date horizon.
- Activity ticket cost is excluded unless a verified price source is added later. Meal, hotel and local transport figures are user-provided estimates.
- Replanning produces a revised draft and resets the approval state. Human approval is required again.
- All third-party API keys are optional/configured locally. Provider terms, rates and quotas can change.

## Academic alignment

| Syllabus concept | Project evidence |
|---|---|
| Goal decomposition | Explicit tasks generated by the Goal Decomposition Agent |
| Planning and decision-making | Place selection, day scheduling and cost model |
| Tool integration | Flight, train, geocoding, weather and map-data connectors |
| Multi-agent system | Named nodes/roles connected through LangGraph |
| Memory | SQLite preference, trip and event tables |
| Human-in-the-loop | Approval and revision controls in UI |
| Dynamic replanning | Rules/LLM revise activities based on weather and human feedback |
| Reliability | Provider errors handled, source notes shown, tests for constraints |
| Responsible AI | No automated booking/payment, no invented transport fares, user approval required |

See `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/API_SETUP.md` and `docs/TEST_PLAN.md` for the report-ready documentation.
