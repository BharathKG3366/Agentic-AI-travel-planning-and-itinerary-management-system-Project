# Suggested 5–7 minute project demonstration

Use a public/synthetic travel request. Do not display API keys or personal account information.

## 1. Problem and architecture (45 seconds)

Explain that a travel chatbot can make suggestions, while this application coordinates research tools, creates a constraint-aware draft, retains decisions, exposes provenance and re-plans after feedback. Show `docs/ARCHITECTURE.md` and identify the LangGraph nodes.

## 2. Live data discovery (60–90 seconds)

- Search a future flight route using a configured provider key, if available.
- Search an Indian train route and show the provider timestamp/fare caveat.
- Open Weather and show forecast source/update time.
- Show an OpenStreetMap place-source link.

If any account/quota is unavailable, show the honest provider error and demonstrate the app using no fabricated transport offers.

## 3. Build an itinerary (90 seconds)

- Enter origin/destination, dates, traveller count, budget and interests.
- Choose a connected transport search or use a previously selected option.
- Click **Research & build itinerary**.
- Explain goal decomposition, tool calls, the generated plan, estimate assumptions and the constraint validator.
- Open the agent trace and data provenance expander.

## 4. Human approval and dynamic re-planning (90 seconds)

- Keep the draft unapproved first.
- Submit feedback such as `rain is expected on Day 2; prefer indoor activities` or `make the pace slower and have fewer places`.
- Show the changed activity schedule and the new `Revised draft — approval required` status.
- Approve the revised itinerary only after discussing the caveats. Emphasize that approval is not a booking.

## 5. Memory and evaluation (60 seconds)

- Open Trip Memory, show saved draft/preferences/event history.
- Download JSON/CSV.
- Run `python -m pytest -q` and report the measured result from your actual local run.

## 6. Closing point

State the implemented limitations honestly: the current app does not book tickets, train seat inventory is not checked by this connector, mapped places do not guarantee opening hours, and accommodation/food/local travel are user estimates rather than live quotes.
