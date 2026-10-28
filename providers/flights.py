"""Flight search through SerpApi's Google Flights engine.

Search only: this connector does not issue tickets or guarantee fares. A fresh
provider response is timestamped; final price and availability must be verified
with the carrier/booking provider before purchase.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
API_URL = "https://serpapi.com/search.json"


def configured() -> bool:
    return bool(os.getenv("SERPAPI_KEY", "").strip())


def _as_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _normalise(item: dict[str, Any], origin: str, destination: str, departure: date,
               return_date: date | None) -> dict[str, Any]:
    segments = item.get("flights") or []
    first = segments[0] if segments else {}
    last = segments[-1] if segments else {}
    dep = first.get("departure_airport") or {}
    arr = last.get("arrival_airport") or {}
    airlines = list(dict.fromkeys(str(s.get("airline")) for s in segments if s.get("airline")))
    duration_mins = item.get("total_duration")
    duration = "Not supplied"
    if isinstance(duration_mins, (float, int)):
        h, m = divmod(int(duration_mins), 60)
        duration = f"{h}h {m}m"
    booking_url = "https://www.google.com/travel/flights?hl=en&curr=INR"
    booking_url += f"#flt={origin}.{destination}.{departure.isoformat()}"
    if return_date:
        booking_url += f"*{origin}.{destination}.{return_date.isoformat()}"
    return {
        "id": str(item.get("booking_token") or item.get("type") or f"{origin}-{destination}-{departure}"),
        "airline": ", ".join(airlines) or "Airline not supplied",
        "origin": str(dep.get("id") or origin),
        "destination": str(arr.get("id") or destination),
        "departure": str(dep.get("time") or "Not supplied"),
        "arrival": str(arr.get("time") or "Not supplied"),
        "stops": max(0, len(segments) - 1),
        "duration": duration,
        "price": _as_float(item.get("price")),
        "currency": "INR",
        "booking_link": booking_url,
        "airline_logo": first.get("airline_logo"),
        "fare_note": "Search-result fare; confirm fare, baggage, cancellation terms and availability before purchase.",
    }


def search_flights(origin: str, destination: str, departure_date: date,
                   adults: int = 1, return_date: date | None = None,
                   max_results: int = 10) -> dict[str, Any]:
    origin, destination = origin.strip().upper(), destination.strip().upper()
    base = {"source": "Google Flights via SerpApi", "offers": [], "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if not configured():
        return {**base, "ok": False, "mode": "not configured", "message": "Flight search needs SERPAPI_KEY in your local .env file. See docs/API_SETUP.md."}
    if any(len(code) != 3 or not code.isalpha() for code in (origin, destination)):
        return {**base, "ok": False, "message": "Use 3-letter IATA airport codes, for example BLR and DEL."}
    if origin == destination:
        return {**base, "ok": False, "message": "Origin and destination must be different."}
    if departure_date < date.today():
        return {**base, "ok": False, "message": "Departure date cannot be in the past."}
    if return_date and return_date < departure_date:
        return {**base, "ok": False, "message": "Return date cannot be earlier than departure date."}
    params: dict[str, Any] = {
        "engine": "google_flights", "departure_id": origin, "arrival_id": destination,
        "outbound_date": departure_date.isoformat(), "type": "1" if return_date else "2",
        "adults": max(1, min(int(adults), 9)), "currency": "INR", "hl": "en", "gl": "in",
        "api_key": os.environ["SERPAPI_KEY"].strip(),
        "no_cache": "true" if os.getenv("SERPAPI_NO_CACHE", "true").lower() in {"1", "true", "yes", "on"} else "false",
    }
    if return_date:
        params["return_date"] = return_date.isoformat()
    try:
        resp = requests.get(API_URL, params=params, timeout=int(os.getenv("API_TIMEOUT_SECONDS", "20")))
        if not resp.ok:
            try:
                detail = resp.json().get("error", resp.text[:250])
            except ValueError:
                detail = resp.text[:250]
            return {**base, "ok": False, "mode": "provider error", "message": f"Flight provider HTTP {resp.status_code}: {detail}"}
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        return {**base, "ok": False, "mode": "provider error", "message": f"Flight search failed: {exc}"}
    if payload.get("error"):
        return {**base, "ok": False, "mode": "provider error", "message": str(payload["error"])}
    raw = (payload.get("best_flights") or []) + (payload.get("other_flights") or [])
    offers = [_normalise(x, origin, destination, departure_date, return_date) for x in raw if isinstance(x, dict)]
    offers.sort(key=lambda o: o["price"] if o["price"] is not None else float("inf"))
    meta = payload.get("search_metadata") or {}
    fresh_requested = params["no_cache"] == "true"
    return {
        **base, "ok": True, "mode": "fresh search requested" if fresh_requested else "cache permitted",
        "freshness": "Provider searched with no_cache=true." if fresh_requested else "Provider cache may have been used.",
        "provider_status": meta.get("status", "not supplied"), "provider_result_count": len(raw),
        "offers": offers[:max(1, min(int(max_results), 20))], "google_flights_url": meta.get("google_flights_url"),
        "message": "Prices and availability can change. Open the comparison link and verify final terms before buying.",
    }
