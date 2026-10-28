"""Indian Railways route and indicative fare data via a RapidAPI provider.

Train schedules are third-party information and can be cached. This connector
intentionally does not claim to check live seat inventory or book tickets.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()
DEFAULT_HOST = "irctc-indian-railway-pnr-status.p.rapidapi.com"
IRCTC_URL = "https://www.irctc.co.in/nget/train-search"


def configured() -> bool:
    return bool(os.getenv("RAPIDAPI_KEY", "").strip())


def _request(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if not configured():
        return {"ok": False, "message": "Train search needs RAPIDAPI_KEY in .env. See docs/API_SETUP.md.", "data": {}}
    host = os.getenv("RAPIDAPI_HOST", DEFAULT_HOST).strip()
    try:
        response = requests.get(f"https://{host}{path}", params=params or {}, headers={
            "X-RapidAPI-Key": os.environ["RAPIDAPI_KEY"].strip(), "X-RapidAPI-Host": host,
        }, timeout=int(os.getenv("API_TIMEOUT_SECONDS", "20")))
        if not response.ok:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text[:300]
            return {"ok": False, "message": f"Railway provider HTTP {response.status_code}: {detail}", "data": {}}
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        return {"ok": False, "message": f"Train search failed: {exc}", "data": {}}
    if payload.get("success") is False:
        return {"ok": False, "message": str(payload.get("message", "Provider reported a failure.")), "data": payload.get("data", {})}
    generated = payload.get("generatedTimeStamp") or payload.get("generated_timestamp")
    if isinstance(generated, (int, float)):
        generated = datetime.fromtimestamp(generated / 1000 if generated > 10_000_000_000 else generated, timezone.utc).isoformat(timespec="seconds")
    return {"ok": True, "message": "Provider response received. Check IRCTC for booking availability and final fare.", "data": payload.get("data", payload), "generated_timestamp": generated}


def search_stations(query: str) -> dict[str, Any]:
    query = query.strip()
    if len(query) < 2:
        return {"ok": False, "message": "Enter at least two characters.", "results": []}
    result = _request(f"/autocomplete/station/{quote(query, safe='')}", {"limit": 10})
    body = result.get("data") or {}
    results = body.get("results", []) if isinstance(body, dict) else []
    return {**result, "results": results}


def search_trains(origin_code: str, destination_code: str, travel_date: date, adults: int = 1) -> dict[str, Any]:
    origin, destination = origin_code.strip().upper(), destination_code.strip().upper()
    base = {"source": "Indian Railways third-party provider via RapidAPI", "trains": [], "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if not configured():
        return {**base, "ok": False, "message": "Train search needs RAPIDAPI_KEY in .env. See docs/API_SETUP.md."}
    if not (2 <= len(origin) <= 8 and origin.isalnum() and 2 <= len(destination) <= 8 and destination.isalnum()):
        return {**base, "ok": False, "message": "Use station codes (2–8 letters/numbers), for example SBC and NDLS."}
    if origin == destination:
        return {**base, "ok": False, "message": "Origin and destination stations must differ."}
    if travel_date < date.today():
        return {**base, "ok": False, "message": "Journey date cannot be in the past."}
    query_date = travel_date.strftime("%d-%m-%Y")
    route = _request(f"/between/{quote(origin, safe='')}/{quote(destination, safe='')}", {"date": query_date})
    if not route.get("ok"):
        return {**base, "ok": False, "message": route.get("message", "Train search failed.")}
    body = route.get("data") or {}
    raw_trains = body.get("trains", []) if isinstance(body, dict) else []
    fare_result = _request("/fare", {"from": origin, "to": destination, "adults": max(1, min(int(adults), 9)), "quota": "GN"})
    fares = {}
    fbody = fare_result.get("data") or {}
    ftrains = fbody.get("trains", []) if isinstance(fbody, dict) else []
    for train in ftrains:
        fares[str(train.get("train_no", ""))] = train.get("fares", [])
    normalized = []
    for train in raw_trains:
        train_no = str(train.get("train_no", ""))
        cheapest, cheapest_class = None, None
        for fare in fares.get(train_no, []):
            try:
                amount = float(fare.get("total_fare"))
            except (TypeError, ValueError):
                continue
            if cheapest is None or amount < cheapest:
                cheapest, cheapest_class = amount, fare.get("class")
        normalized.append({
            "train_no": train_no,
            "train_name": train.get("train_name", "Train name unavailable"),
            "from_station": train.get("from_stn_code", origin),
            "to_station": train.get("to_stn_code", destination),
            "departure": train.get("from_time", "—"), "arrival": train.get("to_time", "—"),
            "duration": train.get("travel_time", "—"), "runs_on": train.get("runs_on", []),
            "indicative_fare": cheapest, "fare_class": cheapest_class,
            "fare_basis": "Third-party indicative fare; may be unavailable or differ at checkout." if cheapest is not None else "Fare not returned by provider.",
            "booking_link": IRCTC_URL,
        })
    normalized.sort(key=lambda t: t["indicative_fare"] if t["indicative_fare"] is not None else float("inf"))
    return {**base, "ok": True, "trains": normalized[:30], "message": route.get("message", "Provider response received."),
            "generated_timestamp": route.get("generated_timestamp"), "fare_lookup_ok": fare_result.get("ok", False),
            "seat_availability_checked": False, "provider_count": len(raw_trains)}
