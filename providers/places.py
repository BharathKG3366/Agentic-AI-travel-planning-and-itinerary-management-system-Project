"""Destination point-of-interest discovery through Open-Meteo geocoding + OSM Overpass.

OSM results represent mapped places, not live opening hours, closures or ticketing.
The service is community-operated: keep queries focused and handle rate limits.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests
from providers.weather import geocode_city

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "VoyageWise-MTech-TravelPlanner/1.0 (educational prototype)"


def search_places(city: str, radius_m: int = 10000, limit: int = 24) -> dict[str, Any]:
    geo = geocode_city(city)
    if not geo.get("ok"):
        return {"ok": False, "source": "OpenStreetMap Overpass", "message": geo.get("message", "Could not resolve destination."), "places": []}
    loc = geo["location"]
    radius = max(1000, min(int(radius_m), 25000))
    lat, lon = loc["latitude"], loc["longitude"]
    # Focused amenity types make this a small, respectful public data query.
    query = f"""[out:json][timeout:18];(
      node[\"tourism\"~\"attraction|museum|viewpoint|zoo|theme_park|gallery\"](around:{radius},{lat},{lon});
      way[\"tourism\"~\"attraction|museum|viewpoint|zoo|theme_park|gallery\"](around:{radius},{lat},{lon});
      relation[\"tourism\"~\"attraction|museum|viewpoint|zoo|theme_park|gallery\"](around:{radius},{lat},{lon});
      node[\"historic\"](around:{radius},{lat},{lon}); way[\"historic\"](around:{radius},{lat},{lon});
      node[\"leisure\"~\"park|nature_reserve\"](around:{radius},{lat},{lon}); way[\"leisure\"~\"park|nature_reserve\"](around:{radius},{lat},{lon});
    );out center;"""
    try:
        response = requests.post(OVERPASS_URL, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=22)
        if not response.ok:
            return {"ok": False, "source": "OpenStreetMap Overpass", "location": loc, "message": f"OpenStreetMap search returned HTTP {response.status_code}. Try again later; the public service may be busy.", "places": []}
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        return {"ok": False, "source": "OpenStreetMap Overpass", "location": loc, "message": f"Place search failed: {exc}", "places": []}
    places = []
    seen = set()
    for element in payload.get("elements", []):
        tags = element.get("tags") or {}
        name = tags.get("name") or tags.get("name:en")
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        center = element.get("center") or {}
        p_lat, p_lon = element.get("lat", center.get("lat")), element.get("lon", center.get("lon"))
        category = tags.get("tourism") or tags.get("historic") or tags.get("leisure") or "place"
        element_type, element_id = element.get("type"), element.get("id")
        osm_url = f"https://www.openstreetmap.org/{element_type}/{element_id}" if element_type and element_id else "https://www.openstreetmap.org/"
        map_url = f"https://www.openstreetmap.org/?mlat={p_lat}&mlon={p_lon}#map=16/{p_lat}/{p_lon}" if p_lat is not None and p_lon is not None else osm_url
        indoor = category in {"museum", "gallery"} or tags.get("indoor") == "yes"
        places.append({"name": name, "category": category.replace("_", " ").title(), "category_raw": category,
                       "latitude": p_lat, "longitude": p_lon, "osm_url": osm_url, "map_url": map_url,
                       "indoor_hint": indoor, "fee_tag": tags.get("fee"), "opening_hours_tag": tags.get("opening_hours"),
                       "description": tags.get("description", "")})
    # Deterministic ordering keeps results stable enough for the planner.
    places.sort(key=lambda p: (not p["indoor_hint"], p["category"], p["name"].casefold()))
    return {"ok": True, "source": "OpenStreetMap via Overpass", "location": loc,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "message": f"Found {len(places)} mapped place(s) near the destination. Opening status, ticket prices and suitability are not verified.",
            "places": places[:max(1, min(int(limit), 50))]}
