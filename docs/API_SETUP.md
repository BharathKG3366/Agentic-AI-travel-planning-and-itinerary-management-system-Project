# API setup and verification

Never paste secrets into chat, screenshots, source files or a public repository. Put keys only in the local `.env` file. Restart the app after editing `.env`.

## 1. Flights — SerpApi / Google Flights

1. Create an account at <https://serpapi.com/users/sign_up>.
2. Open the SerpApi dashboard and copy the API key.
3. In `.env`, set `SERPAPI_KEY=your_private_key`.
4. Keep `SERPAPI_NO_CACHE=true` for fresh-response requests. Fresh requests consume provider quota. To prefer cache when acceptable, set it to `false`.
5. In **Transport Search → Flights**, use IATA codes such as `BLR` and `DEL`, then choose a future date.
6. Inspect errors/usage in your SerpApi dashboard. Don't paste the key or a complete secret-bearing request URL into bug reports.

Official docs: <https://serpapi.com/google-flights-api> · plans: <https://serpapi.com/pricing>.

This returns flight search/comparison offers, not a booking confirmation. The provider's response/price can change. Use the comparison link to verify fare, baggage, cancellation terms and availability before purchasing.

## 2. Trains — Indian Railways provider on RapidAPI

1. Open <https://rapidapi.com/amiteshgupta/api/irctc-indian-railway-pnr-status/details>.
2. Read the current Basic/free and paid plan limits in the provider dashboard. Plan availability and endpoint access may change; a listing is not a guarantee that every endpoint is free.
3. Subscribe to a plan if required and copy the RapidAPI key.
4. Set `RAPIDAPI_KEY=your_private_key` in `.env`. The default host is `irctc-indian-railway-pnr-status.p.rapidapi.com`; check it against the provider dashboard.
5. In **Transport Search → Trains**, use the station lookup form to find codes where the API plan supports autocomplete. Search a route and date.
6. The connector calls `/between/{from}/{to}` and `/fare` using the documented route/fare interface. If your provider plan or schema has changed, the app displays the provider error rather than inventing train data.
7. Verify train, date, quota, seat inventory and final fare through <https://www.irctc.co.in/nget/train-search> before purchase.

Provider endpoints and response examples: <https://rapidapi.com/amiteshgupta/api/irctc-indian-railway-pnr-status/details>.

**Important:** this connector does not reserve seats, buy tickets, check PNR status, or certify real-time seat availability. A fare is labelled indicative when supplied by the provider.

## 3. Weather — Open-Meteo

No API key is configured for this educational prototype. It uses:

- Geocoding: <https://open-meteo.com/en/docs/geocoding-api>
- Forecast: <https://open-meteo.com/en/docs>
- Terms: <https://open-meteo.com/en/terms>

The free endpoint is intended for qualifying non-commercial usage, subject to their terms and attribution. Forecast availability is limited by date horizon; a trip outside the horizon receives a visible note instead of fabricated weather.

## 4. Destination places — OpenStreetMap Overpass

The app queries mapped tourism/historic/park features around a geocoded city. It does not provide authoritative opening hours, closures, ticket fares or route durations.

- Overpass API: <https://overpass-api.de/>
- OpenStreetMap copyright/attribution: <https://www.openstreetmap.org/copyright>

This is a community endpoint. Use it for focused queries, expect temporary rate limits, and retry later if unavailable.

## 5. Optional LLM — Gemini API

1. Open <https://aistudio.google.com/apikey>.
2. Create a key for an eligible free-tier project, if available to your account.
3. Set `GEMINI_API_KEY=your_private_key` in `.env`.
4. The default model is `gemini-3.8-flash`. Confirm model and quota at <https://ai.google.dev/gemini-api/docs/models> and <https://ai.google.dev/gemini-api/docs/pricing>.
5. Restart Streamlit and generate an itinerary. Check **Agent & API Status** for the configured flag; a generation error falls back to the rule-based planner.

Google's free-tier data terms can permit submitted content to be used to improve products. For this academic project, use synthetic travel preferences and avoid confidential or sensitive personal data. Quotas/model access can change.

## Quick verification

- **No keys set:** Weather/place data should be attempted; AI planner falls back locally; flight/train panels explain which key is missing.
- **Flight key set:** Search a future BLR → DEL route and inspect whether offers are returned.
- **Train key set:** First test station autocomplete, then a known route/station-code pair. If the provider errors, check the exact plan/host/path in its dashboard.
- **LLM key set:** Build a trip; the itinerary's `generated_by` field shows whether LLM planning succeeded or fallback was used.
- **Provider unavailable:** no fake fare is produced. Search failures are visible in the app.
