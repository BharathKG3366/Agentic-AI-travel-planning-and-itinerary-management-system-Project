# Test and evaluation plan

## Offline automated tests
Run `python -m pytest -q`. The tests do not call live providers and do not require any keys.

- Flight result normalization: airline, endpoints, price and stops.
- Travel request validation: required fields and sensible ranges.
- Itinerary generation: requested number of days and pending approval state.
- Place provenance: fallback schedule uses only supplied mapped place names.
- Budget constraint: estimated total over budget is surfaced.
- Human-in-the-loop: approval state remains pending after generation and replanning.
- Replanning: rain feedback substitutes mapped indoor places where available; slow-pace feedback removes excess activity blocks; explicit numeric budget changes update and revalidate the budget.
- Weather normalization: WMO codes are represented as readable descriptions.

## Manual provider checks

| Check | Steps | Expected outcome |
|---|---|---|
| No API keys | Start app and open Transport Search | Clear setup guidance; no crash and no fake fare |
| Flight provider | Configure SerpApi key and search a future route | Returned offers include airline, route, provider price and timestamp if supplied |
| Flight no result | Choose valid but unavailable search | Empty result is reported clearly |
| Train provider | Configure RapidAPI key, station lookup and route search | Returned routes and optional fares are labelled third-party/indicative |
| Provider error | Use an invalid test key locally | Error message appears; it is not presented as “no trains found” |
| Weather | Query a city within forecast horizon | Daily conditions and source/retrieval timestamp are displayed |
| Forecast beyond horizon | Request a distant trip date | UI says forecast is unavailable for those dates rather than inventing conditions |
| Place research | Generate trip for a supported city | Mapped places include OpenStreetMap source links where returned |
| LLM absent | Leave `GEMINI_API_KEY` empty | Deterministic plan still renders |
| LLM configured | Add working Gemini API key | `generated_by` indicates LLM path if valid structure is returned; otherwise fallback is used |
| HITL | Try to approve then revise | Approval is explicit; any revision resets it to pending |
| Persistence | Generate/save trip, restart app, open Trip Memory | Trip record and preference memory persist locally |

## Suggested academic metrics

Record these in the final report based on tests you actually run, rather than estimating them:
- Hard-constraint pass rate = test cases with no unreported budget/date/provenance violation ÷ total cases.
- Tool success rate = successful provider responses ÷ attempted requests (report each provider separately).
- Replanning success rate = feedback tests producing an expected structural revision ÷ all tested feedback cases.
- Human gate correctness = generated/revised drafts staying pending until approval.
- Data transparency = provider outputs with visible source/freshness/limitation label.

Do not claim exact success percentages until the tests and manual provider checks have been executed and the results recorded.
