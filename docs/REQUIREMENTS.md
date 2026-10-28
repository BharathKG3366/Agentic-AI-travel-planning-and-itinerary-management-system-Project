# Software requirements specification

## Project title
Agentic AI-Based Autonomous Travel Planning and Itinerary Management System (VoyageWise AI)

## Problem statement
Travel planning requires users to align dates, preferences, budget, destinations, transport choices and changing conditions. A text-only assistant can suggest ideas but may not preserve source provenance, validate constraints, orchestrate tools, remember decisions or revise an itinerary based on feedback. This project implements a travel research and planning workflow with distinct agent roles, structured constraints, optional LLM reasoning, persistent memory, human approval and replanning.

## Objectives
1. Accept a structured user travel goal.
2. Decompose the goal into research, transport, planning and validation tasks.
3. Search flight options and train routes through configured external providers.
4. Retrieve destination place data and weather forecasts from public data endpoints.
5. Create day-by-day itinerary suggestions based on researched places and user preferences.
6. Estimate cost components with transparent assumptions and validate budget constraints deterministically.
7. Store selected preferences, draft itineraries, approvals and agent events locally.
8. Accept human feedback and generate a revised itinerary, requiring approval again.
9. Provide a responsive light/dark interface, data-provenance visibility and exports.
10. Evaluate functional correctness and provider failure behaviour through offline tests.

## Users
- Primary user: student/developer evaluating the mini-project.
- Intended application user: traveller creating a trip draft and comparing provider-returned information.

## Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | The system shall collect origin, destination, departure date, trip length, travellers, budget and interests. |
| FR-02 | The system shall decompose each planning request into named tasks. |
| FR-03 | The system shall query a flight search provider when a valid API key is configured. |
| FR-04 | The system shall query an Indian train route/fare provider when a valid API key is configured. |
| FR-05 | The system shall retrieve forecast data through Open-Meteo when available. |
| FR-06 | The system shall query mapped destination points of interest through OpenStreetMap Overpass when available. |
| FR-07 | The system shall create a day-by-day itinerary with times, selected named places, source links and indoor alternatives where available. |
| FR-08 | The system shall ensure named attractions in LLM output match researched place names or remove them. |
| FR-09 | The system shall estimate food, accommodation and local transport costs from user-entered assumptions and include a provider-returned transport fare only when available. |
| FR-10 | The system shall flag an estimated total that exceeds the user's budget. |
| FR-11 | The system shall pause for human approval after generation and after every revision. |
| FR-12 | The system shall persist preference memory, trip drafts and agent events in local SQLite storage. |
| FR-13 | The system shall support feedback-based revisions for weather/indoor preferences, nature preferences, slower pace and explicit numeric budget changes. |
| FR-14 | The system shall label provider source, timestamps and known limitations. |
| FR-15 | The system shall handle missing keys, provider HTTP errors, bad JSON, no-result queries and model failure without fabricating live transport data. |
| FR-16 | The system shall export itinerary details to JSON and activity information to CSV. |

## Non-functional requirements
- Beginner-runnable on Python 3.12 and a desktop browser.
- No mandatory paid key for app startup or local rule-based itinerary generation.
- API keys must be stored in `.env` and excluded from source control.
- External requests use timeouts and descriptive errors.
- Hard budget checks use deterministic Python logic rather than trusting the LLM alone.
- No ticket-purchase, payment or hotel-booking action is exposed.
- UI supports Streamlit light and dark themes.
- Tests must run offline without API credentials.

## Scope boundaries
Included: search and compare provider-returned flight/trains results, map-based place research, weather forecast, itinerary drafting, explicit estimates, local memory, HITL approval, feedback replanning and exports.

Not included: actually buying tickets, reserving seats, live PNR status, live hotel availability/prices, automatic payments, guaranteed venue opening status, authoritative route navigation, or autonomous external transactions.

## Acceptance criteria
- Application starts using the documented commands.
- With no credentials, core UI and rule-based planner can operate; missing integrations are labelled.
- Flight and train connectors normalize provider-returned data and handle missing keys/provider errors.
- At least one itinerary is generated and structurally validated without an LLM key.
- Replanning makes actual changes to one or more activities or updates a requested numeric budget, and resets approval state.
- A user can approve a draft; approval state is stored locally and does not imply a booking.
- Unit tests pass without external network access.
