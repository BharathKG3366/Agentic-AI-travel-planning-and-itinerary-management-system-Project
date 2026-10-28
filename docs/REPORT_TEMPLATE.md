# Mini-project report template

Replace bracketed prompts with your own actual implementation details and measured results. Do not report unperformed tests as completed results.

## Title
Agentic AI-Based Autonomous Travel Planning and Itinerary Management System

## Abstract
[Write 150–250 words describing the travel-planning problem, the multi-agent workflow, external tools, constraints, memory, human approval, dynamic replanning, and results you measured. State clearly that the system searches/plans but does not purchase tickets.]

## 1. Introduction
[Explain travel planning as a multi-constraint decision problem. Differentiate static text generation from a tool-using workflow that can react to new information.]

## 2. Problem statement
[Describe the issues: fragmented transport/forecast/attraction research, budget feasibility, user preference memory, and itinerary changes.]

## 3. Objectives
- Decompose the travel goal into actionable tasks.
- Coordinate specialized agent roles.
- Retrieve flight, train-route, weather and mapped-place information through external tools.
- Generate and validate a multi-day itinerary.
- Preserve preferences and trip decisions locally.
- Request human approval and re-plan after feedback.
- Evaluate correctness, provider failures and constraint handling.

## 4. Scope and limitations
[Document exact APIs configured, their account tiers, what was tested live, and the limitations listed in README.md.]

## 5. System design
[Insert the architecture flow from `docs/ARCHITECTURE.md`. Include agent responsibilities, data flow, data sources, state and error-handling rules.]

## 6. Implementation
Describe the Streamlit UI, LangGraph workflow, Pydantic request model, transport/weather/place connectors, deterministic constraint validator, optional Gemini model path, SQLite memory, HITL controls, and replanning rules.

## 7. Testing methodology
Use `docs/TEST_PLAN.md`. Record the date, provider, route/city, configuration status and observed result for manual integration tests.

## 8. Results
| Metric | Result measured by you | Test evidence |
|---|---|---|
| Offline automated tests passed | [fill in] | Terminal output |
| Flight provider tests | [fill in; include not configured if not available] | Screenshot/log without secrets |
| Train route query | [fill in] | Screenshot with fare limitations |
| Weather/places query | [fill in] | Source/time displayed |
| Replanning cases passed | [fill in] | Before/after itinerary |
| Budget cases correctly flagged | [fill in] | Validation output |

## 9. Safety and responsible AI
[Discuss fabricated-fare prevention, data provenance, model output filtering, provider errors, approval gates, secrets management and free-tier privacy considerations.]

## 10. Conclusion and future work
[Summarize measured results. Potential future work: official ticketing partner APIs, accommodation providers, route-distance optimization, a true approval-resume checkpoint, authenticated multi-user deployment, notification-based replanning, and more extensive evaluations.]

## References
- SerpApi Google Flights API documentation: https://serpapi.com/google-flights-api
- Indian Railway API provider documentation: https://rapidapi.com/amiteshgupta/api/irctc-indian-railway-pnr-status/details
- Open-Meteo documentation: https://open-meteo.com/en/docs
- OpenStreetMap copyright and attribution: https://www.openstreetmap.org/copyright
- Gemini API models: https://ai.google.dev/gemini-api/docs/models
- LangGraph docs: https://docs.langchain.com/oss/python/langgraph/overview
- Streamlit theming docs: https://docs.streamlit.io/develop/concepts/configuration/theming
