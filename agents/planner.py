"""Constraint-aware itinerary planner and feedback-driven replanner.

The LLM may suggest a sequence, but hard budget/date checks remain deterministic.
Named attractions are constrained to places returned by the connected place source.
"""
from __future__ import annotations

import json
import math
import os
import re
from datetime import date, timedelta
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()


class TripRequest(BaseModel):
    origin_city: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    departure_date: date
    days: int = Field(ge=1, le=21)
    travelers: int = Field(ge=1, le=9)
    budget_inr: float = Field(gt=0)
    interests: list[str] = Field(default_factory=list)
    transport_mode: str = "None"
    origin_code: str = ""
    destination_code: str = ""
    food_budget_per_person_per_day: float = Field(default=800, ge=0, le=20000)
    accommodation_per_room_per_night: float = Field(default=1800, ge=0, le=100000)
    local_transport_per_person_per_day: float = Field(default=350, ge=0, le=10000)
    notes: str = ""


DAY_KEYS = {"day", "date", "title", "activities"}


def decompose_goal(request: TripRequest) -> list[dict[str, str]]:
    return [
        {"task": "Normalize the goal", "detail": f"Plan {request.days} day(s) from {request.origin_city} to {request.destination} for {request.travelers} traveller(s)."},
        {"task": "Research destination", "detail": "Fetch mapped attractions and the available forecast; preserve source timestamps."},
        {"task": "Research transport", "detail": f"Transport preference: {request.transport_mode}; search is attempted only when requested and configured."},
        {"task": "Construct itinerary", "detail": "Schedule verified place names and clearly mark unverified opening hours/ticket prices."},
        {"task": "Validate constraints", "detail": "Calculate budget components and flag overruns without silently changing user inputs."},
        {"task": "Human approval", "detail": "Present a draft for review; no booking/payment actions are performed."},
    ]


def _money(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) and number >= 0 else None
    except (TypeError, ValueError):
        return None


def _select_places(places: list[dict[str, Any]], request: TripRequest) -> list[dict[str, Any]]:
    if not places:
        return []
    interests = " ".join(request.interests).casefold()
    def score(place: dict[str, Any]) -> tuple[int, str]:
        hay = (place.get("name", "") + " " + place.get("category", "") + " " + place.get("description", "")).casefold()
        match = sum(2 for word in re.findall(r"[a-z]{3,}", interests) if word in hay)
        return (-match, str(place.get("name", "")).casefold())
    return sorted(places, key=score)


def _fallback_days(request: TripRequest, places: list[dict[str, Any]], weather: dict[str, Any]) -> list[dict[str, Any]]:
    ranked = _select_places(places, request)
    daily_forecast = {str(item.get("date")): item for item in weather.get("forecast", [])} if weather.get("ok") else {}
    indoor = [p for p in ranked if p.get("indoor_hint")]
    days = []
    for i in range(request.days):
        day_date = request.departure_date + timedelta(days=i)
        forecast = daily_forecast.get(day_date.isoformat(), {})
        rainy = (forecast.get("precipitation_probability") or 0) >= 50 or "rain" in str(forecast.get("description", "")).casefold() or "thunder" in str(forecast.get("description", "")).casefold()
        # Deterministic round-robin selection, two unique places per day where possible.
        selected: list[dict[str, Any]] = []
        for offset in (i * 2, i * 2 + 1):
            if ranked:
                candidate = ranked[offset % len(ranked)]
                if candidate not in selected:
                    selected.append(candidate)
        if rainy and indoor:
            selected = indoor[:2]
        activities = []
        times = ["09:30", "15:00"]
        for j, place in enumerate(selected):
            backup = next((p for p in indoor if p.get("name") != place.get("name")), None)
            activities.append({
                "time": times[j], "activity": f"Visit {place['name']}", "place_name": place["name"],
                "location": place["name"], "category": place.get("category", "Place"),
                "estimated_cost_inr": 0, "cost_basis": "Attraction entry fee was not supplied by the source; excluded until verified.",
                "reason": f"Mapped {place.get('category', 'place').lower()} found near {request.destination}. Check opening hours before going.",
                "indoor_alternative": backup.get("name") if backup else "Choose an indoor attraction after checking its current opening hours.",
                "source_url": place.get("osm_url", ""), "map_url": place.get("map_url", ""),
            })
        if not activities:
            activities = [{"time": "10:00", "activity": f"Flexible exploration around {request.destination}", "place_name": "", "location": request.destination,
                           "category": "Flexible", "estimated_cost_inr": 0, "cost_basis": "No verified attraction found; no attraction cost included.",
                           "reason": "The place provider returned no usable named attractions. Search local official visitor information before travelling.",
                           "indoor_alternative": "Visit a local indoor venue after checking its details.", "source_url": "", "map_url": ""}]
        weather_note = f"Forecast: {forecast.get('description', 'not available')}" if forecast else "Forecast not available for this date; check again nearer departure."
        days.append({"day": i + 1, "date": day_date.isoformat(), "title": f"Day {i + 1} · {day_date.strftime('%A, %d %b')}",
                     "weather_note": weather_note, "activities": activities})
    return days


def _gemini_schedule(request: TripRequest, places: list[dict[str, Any]], weather: dict[str, Any]) -> list[dict[str, Any]] | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        slim_places = [{"name": p.get("name"), "category": p.get("category"), "indoor_hint": p.get("indoor_hint", False)} for p in places[:40]]
        forecast = weather.get("forecast", []) if weather.get("ok") else []
        prompt = f"""You are the itinerary scheduling agent in an academic multi-agent travel system.
Make a practical, clearly labelled itinerary draft. Do not invent named attractions: every place_name must exactly match one name in VERIFIED_PLACES; if there are no places, use an empty place_name and a generic flexible activity. Never make up opening hours, ticket prices, availability, transport schedules, or live facts. Include exactly {request.days} days and at most 2 named attraction visits per day. Respect interests and avoid outdoor places on days with precipitation probability >= 50 where indoor places exist. Use local city-time display, not inferred exact travel durations. All activity cost numbers must be 0 unless supplied by the user; meal/lodging/transport costs are calculated separately.
Return JSON with key days; each day has day (1..N), date (YYYY-MM-DD), title, weather_note, activities. Each activity has time (HH:MM), activity, place_name, reason. No markdown fences.
REQUEST={request.model_dump(mode='json')}
VERIFIED_PLACES={json.dumps(slim_places, ensure_ascii=False)}
WEATHER={json.dumps(forecast, ensure_ascii=False)}"""
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"), contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.25),
        )
        payload = json.loads((response.text or "").strip())
        days = payload.get("days")
        if not isinstance(days, list) or len(days) != request.days:
            return None
        by_name = {str(p.get("name", "")).casefold(): p for p in places}
        safe_days = []
        backup_names = [p.get("name") for p in places if p.get("indoor_hint") and p.get("name")]
        for index, raw_day in enumerate(days):
            if not isinstance(raw_day, dict):
                return None
            activities = []
            for raw_item in (raw_day.get("activities") or [])[:2]:
                if not isinstance(raw_item, dict):
                    continue
                requested_name = str(raw_item.get("place_name", "")).strip()
                place = by_name.get(requested_name.casefold()) if requested_name else None
                # Reject model-invented place names; never display them as researched results.
                if not place:
                    continue
                backup = next((p for p in backup_names if p.casefold() != requested_name.casefold()), None)
                activities.append({"time": str(raw_item.get("time", "10:00"))[:5], "activity": f"Visit {place['name']}", "place_name": place["name"],
                                   "location": place["name"], "category": place.get("category", "Place"), "estimated_cost_inr": 0,
                                   "cost_basis": "Entry fee not supplied; excluded until verified.",
                                   "reason": str(raw_item.get("reason", "Selected from the place source."))[:300],
                                   "indoor_alternative": backup or "Check for an indoor alternative before travelling.",
                                   "source_url": place.get("osm_url", ""), "map_url": place.get("map_url", "")})
            # Guarantee a useful day even if the LLM returned invented locations.
            if not activities:
                fallback = _fallback_days(request, places, weather)[index]
                activities = fallback["activities"]
            day_date = request.departure_date + timedelta(days=index)
            safe_days.append({"day": index + 1, "date": day_date.isoformat(),
                              "title": str(raw_day.get("title", f"Day {index + 1}"))[:100],
                              "weather_note": str(raw_day.get("weather_note", "Forecast is subject to change."))[:180],
                              "activities": activities})
        return safe_days
    except Exception:
        return None


def _transport_cost(transport: dict[str, Any] | None) -> tuple[float, str]:
    if not transport:
        return 0.0, "No transport option selected; ticket cost is excluded."
    mode = str(transport.get("mode", "Transport"))
    raw = transport.get("price")
    if raw is None:
        raw = transport.get("indicative_fare")
    price = _money(raw)
    if price is None:
        return 0.0, f"{mode} option selected, but the provider supplied no usable fare; transport cost is excluded."
    if mode.lower() == "train":
        return price, "Third-party indicative train fare for searched passenger count/route; verify on IRCTC."
    return price, "Provider-returned flight fare; reconfirm before purchase."


def _cost_summary(request: TripRequest, transport: dict[str, Any] | None) -> dict[str, Any]:
    transport_cost, transport_basis = _transport_cost(transport)
    nights = max(0, request.days - 1)
    rooms = max(1, math.ceil(request.travelers / 2))
    food = request.food_budget_per_person_per_day * request.travelers * request.days
    lodging = request.accommodation_per_room_per_night * rooms * nights
    local = request.local_transport_per_person_per_day * request.travelers * request.days
    total = round(transport_cost + food + lodging + local, 2)
    return {"currency": "INR", "transport_inr": round(transport_cost, 2), "transport_basis": transport_basis,
            "food_inr": round(food, 2), "food_basis": "User-provided per-person/day estimate; not a live restaurant quote.",
            "accommodation_inr": round(lodging, 2), "accommodation_basis": f"User-provided room/night estimate × {rooms} room(s) × {nights} night(s); not a live hotel quote.",
            "local_transport_inr": round(local, 2), "local_transport_basis": "User-provided per-person/day estimate; not a live taxi quote.",
            "known_attraction_fees_inr": 0.0, "attraction_basis": "No live entry prices supplied; exclude until verified.",
            "total_estimated_inr": total, "budget_inr": round(request.budget_inr, 2),
            "remaining_inr": round(request.budget_inr - total, 2)}


def validate_itinerary(itinerary: dict[str, Any], request: TripRequest, places: list[dict[str, Any]] | None = None) -> list[str]:
    issues: list[str] = []
    days = itinerary.get("days", [])
    if len(days) != request.days:
        issues.append(f"Expected {request.days} days but received {len(days)}.")
    if len({d.get("day") for d in days}) != len(days):
        issues.append("Duplicate day numbers found.")
    if places is not None:
        known = {str(p.get("name", "")).casefold() for p in places}
        for d in days:
            for item in d.get("activities", []):
                name = str(item.get("place_name", "")).strip()
                if name and name.casefold() not in known:
                    issues.append(f"Unverified place name in itinerary: {name}.")
    cost = itinerary.get("cost_summary", {})
    total = _money(cost.get("total_estimated_inr"))
    if total is not None and total > request.budget_inr:
        issues.append(f"Estimated costs ₹{total:,.0f} exceed the budget ₹{request.budget_inr:,.0f}. Revise assumptions or budget before approval.")
    # Check activity times and ensure output cannot silently contain a malformed day object.
    for day in days:
        if not isinstance(day, dict):
            issues.append("An itinerary day is not a valid object.")
            continue
        for activity in day.get("activities", []):
            if not isinstance(activity, dict):
                issues.append("An activity is not a valid object.")
                continue
            time_str = str(activity.get("time", ""))
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time_str):
                issues.append(f"Invalid time format: {time_str}.")
    return list(dict.fromkeys(issues))


def build_itinerary(request: TripRequest, place_result: dict[str, Any] | None = None,
                    weather_result: dict[str, Any] | None = None,
                    transport: dict[str, Any] | None = None) -> dict[str, Any]:
    place_result = place_result or {"ok": False, "places": [], "message": "Place research not run."}
    weather_result = weather_result or {"ok": False, "forecast": [], "message": "Weather research not run."}
    places = place_result.get("places", []) if place_result.get("ok") else []
    use_llm = bool(os.getenv("GEMINI_API_KEY", "").strip())
    days = _gemini_schedule(request, places, weather_result) if use_llm else None
    generated_by = "Gemini-assisted planning with place-name verification" if days else "Rule-based planner with researched place data"
    if not days:
        days = _fallback_days(request, places, weather_result)
    cost_summary = _cost_summary(request, transport)
    itinerary = {
        "title": f"{request.origin_city} to {request.destination}",
        "summary": f"A {request.days}-day draft for {request.travelers} traveller(s), prioritizing {', '.join(request.interests) if request.interests else 'balanced local exploration'}. Named attractions come from the place source when available.",
        "origin_city": request.origin_city, "destination": request.destination,
        "departure_date": request.departure_date.isoformat(), "days_count": request.days,
        "travelers": request.travelers, "interests": request.interests, "notes": request.notes,
        "days": days, "cost_summary": cost_summary,
        "research": {"places": {"ok": bool(place_result.get("ok")), "source": place_result.get("source", "Unavailable"),
                                  "retrieved_at_utc": place_result.get("retrieved_at_utc"), "count": len(places), "message": place_result.get("message", "")},
                     "weather": {"ok": bool(weather_result.get("ok")), "source": weather_result.get("source", "Unavailable"),
                                 "retrieved_at_utc": weather_result.get("retrieved_at_utc"), "message": weather_result.get("message", "")}},
        "transport": transport,
        "generated_by": generated_by,
        "assumptions": ["This is an itinerary draft, not a booking.", "Attraction opening hours, closures and entry fees are not verified by this app.",
                        "Accommodation, meals and local transport are user-provided estimates, not live quotes.",
                        "Flight fare and third-party train fare may change; confirm on the provider/official site before paying."],
        "change_log": [], "requires_human_approval": True, "approval_status": "Pending approval",
    }
    itinerary["validation_issues"] = validate_itinerary(itinerary, request, places)
    itinerary["agent_trace"] = []
    return itinerary


def apply_transport_option(itinerary: dict[str, Any], request: TripRequest,
                           transport: dict[str, Any] | None, places: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    updated = dict(itinerary)
    updated["transport"] = transport
    updated["cost_summary"] = _cost_summary(request, transport)
    updated["validation_issues"] = validate_itinerary(updated, request, places)
    updated["requires_human_approval"] = True
    updated["approval_status"] = "Updated draft — approval required"
    return updated


def _gemini_replan(itinerary: dict[str, Any], request: TripRequest, feedback: str,
                   places: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not os.getenv("GEMINI_API_KEY", "").strip():
        return None
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "").strip())
        prompt = f"""Revise this travel itinerary based on the traveller's feedback. Do not invent places; use only exact `place_name` values from VERIFIED_PLACES, otherwise use empty `place_name` with generic flexible activity. Keep exactly {request.days} days, times HH:MM, do not claim to book anything, do not create fake live price/weather facts, and keep named visits to max two per day. Return JSON only with `days` array and `change_summary` string. Preserve unchanged details where possible.
FEEDBACK={feedback}
REQUEST={request.model_dump(mode='json')}
VERIFIED_PLACES={json.dumps([{'name':p.get('name'),'category':p.get('category'),'indoor_hint':p.get('indoor_hint')} for p in places], ensure_ascii=False)}
CURRENT_ITINERARY={json.dumps(itinerary.get('days', []), ensure_ascii=False)}"""
        result = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"), contents=prompt,
                                                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
        payload = json.loads((result.text or "").strip())
        days = payload.get("days")
        if not isinstance(days, list) or len(days) != request.days:
            return None
        lookup = {str(p.get("name", "")).casefold(): p for p in places}
        for day in days:
            day_date = str(day.get("date", ""))
            for activity in day.get("activities", []):
                name = str(activity.get("place_name", "")).casefold().strip()
                place = lookup.get(name) if name else None
                if name and not place:
                    activity["place_name"] = ""
                    activity["location"] = request.destination
                    activity["activity"] = "Flexible exploration near the destination"
                    activity["source_url"] = ""
                    activity["map_url"] = ""
                elif place:
                    activity["location"] = place["name"]
                    activity["source_url"] = place.get("osm_url", "")
                    activity["map_url"] = place.get("map_url", "")
                activity["estimated_cost_inr"] = 0
                activity["cost_basis"] = "Attraction entry price not verified."
        revised = dict(itinerary)
        revised["days"] = days
        revised["replan_method"] = "Gemini-assisted with place verification"
        revised["change_log"] = list(itinerary.get("change_log", [])) + [{"feedback": feedback, "summary": str(payload.get("change_summary", "Itinerary revised."))}]
        return revised
    except Exception:
        return None


def replan_from_feedback(itinerary: dict[str, Any], feedback: str, request: TripRequest,
                         places: list[dict[str, Any]] | None = None,
                         weather: dict[str, Any] | None = None) -> dict[str, Any]:
    """Revise activities and constraints; every revised plan returns to human approval.

    Gemini is used when configured. A deterministic set of rules provides a useful
    offline fallback, so replanning still works without an LLM key.
    """
    feedback = feedback.strip()
    if not feedback:
        return {**itinerary, "replan_error": "Please describe the desired change."}
    places = places or []
    text = feedback.casefold()
    revised_by_llm = _gemini_replan(itinerary, request, feedback, places)
    method = "Gemini-assisted with place verification" if revised_by_llm else "Deterministic feedback rules"
    revised = revised_by_llm or json.loads(json.dumps(itinerary))
    changes: list[str] = []
    day_match = re.search(r"\bday\s*(\d{1,2})\b", text)
    target_day = int(day_match.group(1)) if day_match else None
    relevant_days = [d for d in revised.get("days", []) if target_day is None or d.get("day") == target_day]
    if target_day is not None and not relevant_days:
        revised["replan_error"] = f"Day {target_day} doesn't exist; no itinerary changes were applied."
        return revised

    # Explicit numeric budget changes update the hard constraint; costs are not
    # silently fabricated or modified to make a plan appear feasible.
    budget_match = re.search(r"(?:₹|\binr\b|\brs\.?\s*)([\d,]+)", feedback, flags=re.IGNORECASE)
    if not budget_match:
        budget_match = re.search(r"(?:budget|spend|cost)\s*(?:to|of|at)?\s*([\d,]{4,})", feedback, flags=re.IGNORECASE)
    if "budget" in text or "spend" in text or "cost" in text:
        if budget_match:
            new_budget = float(budget_match.group(1).replace(",", ""))
            if new_budget <= 0:
                revised["replan_error"] = "The revised budget must be greater than zero."
                return revised
            request.budget_inr = new_budget
            revised.setdefault("cost_summary", {})["budget_inr"] = round(new_budget, 2)
            revised["cost_summary"]["remaining_inr"] = round(new_budget - float(revised["cost_summary"].get("total_estimated_inr", 0)), 2)
            changes.append(f"Budget constraint updated to ₹{new_budget:,.0f}; existing estimates were preserved and revalidated.")
        elif not revised_by_llm:
            revised["replan_error"] = "Please include a target amount, for example: 'reduce the total budget to ₹20000'. No changes were applied."
            return revised

    # Apply local rules only when no LLM plan came back. Never double-transform
    # an LLM-revised schedule with the rule-based schedule changes.
    if not revised_by_llm:
        if any(word in text for word in ("rain", "raining", "wet", "storm", "indoor")):
            indoor_places = [p for p in places if p.get("indoor_hint")]
            for day in relevant_days:
                for activity in day.get("activities", []):
                    chosen = next((p for p in indoor_places if p.get("name", "").casefold() != str(activity.get("place_name", "")).casefold()), None)
                    if chosen:
                        old_name = activity.get("place_name") or activity.get("activity")
                        activity.update({"activity": f"Indoor option: {chosen['name']}", "place_name": chosen["name"], "location": chosen["name"],
                                         "category": chosen.get("category", "Indoor attraction"), "source_url": chosen.get("osm_url", ""),
                                         "map_url": chosen.get("map_url", ""), "reason": "Swapped during replanning for an indoor-mapped place; confirm it is open."})
                        changes.append(f"Day {day['day']}: {old_name} → {chosen['name']}")
                    else:
                        old_name = activity.get("activity", "Activity")
                        activity.update({"activity": "Weather-flexible indoor alternative (verify locally)", "place_name": "", "location": request.destination,
                                         "source_url": "", "map_url": "", "reason": "Changed by feedback rule; a specific indoor venue could not be verified."})
                        changes.append(f"Day {day['day']}: {old_name} → generic indoor alternative")
        elif any(word in text for word in ("nature", "outdoor", "scenic", "viewpoint", "park")):
            nature = [p for p in places if any(tag in (str(p.get("category", "")) + " " + str(p.get("name", ""))).casefold()
                                               for tag in ("park", "nature", "viewpoint", "garden", "waterfall", "beach", "lake"))]
            if nature:
                for idx, day in enumerate(relevant_days):
                    for a_idx, activity in enumerate(day.get("activities", [])):
                        place = nature[(idx + a_idx) % len(nature)]
                        old = activity.get("place_name") or activity.get("activity")
                        activity.update({"activity": f"Explore {place['name']}", "place_name": place["name"], "location": place["name"],
                                         "category": place.get("category", "Outdoor attraction"), "source_url": place.get("osm_url", ""), "map_url": place.get("map_url", ""),
                                         "reason": "Prioritized based on the requested nature/scenic preference; verify conditions before travel."})
                        changes.append(f"Day {day['day']}: {old} → {place['name']}")
        elif any(word in text for word in ("less walking", "avoid walking", "less travel", "shorter", "fewer places", "slow pace", "relaxed")):
            for day in relevant_days:
                if len(day.get("activities", [])) > 1:
                    day["activities"] = day["activities"][:1]
                    changes.append(f"Day {day['day']}: reduced the activity count for a lighter schedule")
        elif not any(word in text for word in ("budget", "spend", "cost")):
            options = [p for p in places if p.get("name")]
            if options:
                for idx, day in enumerate(relevant_days):
                    for j, activity in enumerate(day.get("activities", [])):
                        place = options[(idx + j + 1) % len(options)]
                        old = activity.get("place_name") or activity.get("activity")
                        activity.update({"activity": f"Visit {place['name']}", "place_name": place["name"], "location": place["name"],
                                         "category": place.get("category", "Place"), "source_url": place.get("osm_url", ""), "map_url": place.get("map_url", ""),
                                         "reason": f"Changed during replanning in response to: {feedback[:140]}. Check current details before travelling."})
                        changes.append(f"Day {day['day']}: {old} → {place['name']}")
            else:
                for day in relevant_days:
                    day["title"] = f"{day['title']} · revised"
                    changes.append(f"Day {day['day']}: marked for user review based on feedback")
    else:
        changes.append("LLM revised the activity schedule; deterministic validation is applied next.")

    revised["replan_method"] = method
    revised.setdefault("change_log", []).append({"feedback": feedback,
        "summary": "; ".join(changes) or "The requested change was reviewed; no concrete activity replacement was necessary.", "changes": changes})
    revised["requires_human_approval"] = True
    revised["approval_status"] = "Revised draft — approval required"
    revised["validation_issues"] = validate_itinerary(revised, request, places)
    revised.setdefault("agent_trace", []).append({"agent": "Replanning Agent", "status": "completed", "detail": f"Replanned using {method}; {len(changes)} change(s)."})
    return revised
