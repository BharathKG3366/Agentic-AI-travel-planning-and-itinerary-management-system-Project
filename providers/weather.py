"""Open-Meteo geocoding and forecast connector (no key for eligible use)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

TIMEOUT = 15
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Freezing drizzle", 57: "Dense freezing drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Heavy freezing rain", 71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains", 80: "Rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Snow showers", 86: "Heavy snow showers", 95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def geocode_city(city: str) -> dict[str, Any]:
    city = city.strip()
    if len(city) < 2:
        return {"ok": False, "message": "Enter a destination with at least two characters."}
    try:
        response = requests.get(GEOCODE_URL, params={"name": city, "count": 5, "language": "en", "format": "json"}, timeout=TIMEOUT)
        response.raise_for_status()
        results = response.json().get("results") or []
    except (requests.RequestException, ValueError) as exc:
        return {"ok": False, "message": f"Location lookup failed: {exc}"}
    if not results:
        return {"ok": False, "message": f"No geocoding match found for '{city}'. Try a city and country, e.g. 'Mysuru, India'."}
    # Prefer India where multiple geocoding matches exist; otherwise use provider ranking.
    item = next((x for x in results if x.get("country_code", "").upper() == "IN"), results[0])
    return {"ok": True, "location": {"name": item.get("name", city), "country": item.get("country", ""),
            "admin1": item.get("admin1", ""), "latitude": item["latitude"], "longitude": item["longitude"],
            "timezone": item.get("timezone", "auto")}}


def get_weather(city: str, start_date: date | None = None, end_date: date | None = None) -> dict[str, Any]:
    geo = geocode_city(city)
    if not geo.get("ok"):
        return geo
    start_date = start_date or date.today()
    end_date = end_date or (start_date + timedelta(days=5))
    if end_date < start_date:
        return {"ok": False, "message": "Forecast end date must be on or after start date."}
    max_forecast_date = date.today() + timedelta(days=15)
    if start_date > max_forecast_date:
        return {"ok": False, "location": geo["location"], "message": "This trip starts outside the public forecast horizon. Add weather closer to departure; do not infer conditions this far ahead."}
    # Request only the range Open-Meteo can cover; explain if a journey extends past it.
    actual_end = min(end_date, max_forecast_date)
    loc = geo["location"]
    params = {"latitude": loc["latitude"], "longitude": loc["longitude"],
              "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
              "timezone": loc.get("timezone", "auto"), "start_date": max(start_date, date.today()).isoformat(), "end_date": actual_end.isoformat()}
    try:
        response = requests.get(FORECAST_URL, params=params, timeout=TIMEOUT)
        if not response.ok:
            return {"ok": False, "location": loc, "message": f"Weather provider returned HTTP {response.status_code}: {response.text[:220]}"}
        daily = response.json().get("daily") or {}
    except (requests.RequestException, ValueError) as exc:
        return {"ok": False, "location": loc, "message": f"Weather forecast failed: {exc}"}
    dates = daily.get("time", [])
    forecast = []
    for i, day in enumerate(dates):
        code = (daily.get("weather_code") or [None] * len(dates))[i]
        pop = (daily.get("precipitation_probability_max") or [None] * len(dates))[i]
        forecast.append({"date": day, "description": WMO_CODES.get(code, "Conditions unavailable"),
                         "weather_code": code,
                         "temperature_max_c": (daily.get("temperature_2m_max") or [None] * len(dates))[i],
                         "temperature_min_c": (daily.get("temperature_2m_min") or [None] * len(dates))[i],
                         "precipitation_probability": pop})
    note = "Forecast data from Open-Meteo; model predictions are not guarantees."
    if end_date > actual_end:
        note += f" Forecast currently covers through {actual_end.isoformat()} only; later trip days need a new forecast nearer departure."
    return {"ok": True, "location": loc, "forecast": forecast, "source": "Open-Meteo", "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "message": note}
