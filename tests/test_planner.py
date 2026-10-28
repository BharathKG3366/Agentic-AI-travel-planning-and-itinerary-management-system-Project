from datetime import date, timedelta

from agents.planner import TripRequest, apply_transport_option, build_itinerary, replan_from_feedback, validate_itinerary


def request(future_date=None, **overrides):
    data = {
        "origin_city": "Bengaluru",
        "destination": "Kochi",
        "departure_date": future_date or date.today() + timedelta(days=5),
        "days": 3,
        "travelers": 2,
        "budget_inr": 25000,
        "interests": ["nature", "local food"],
        "transport_mode": "None",
        "food_budget_per_person_per_day": 800,
        "accommodation_per_room_per_night": 1800,
        "local_transport_per_person_per_day": 350,
    }
    data.update(overrides)
    return TripRequest(**data)


def place(name, category, indoor=False):
    return {"name": name, "category": category, "indoor_hint": indoor,
            "osm_url": f"https://www.openstreetmap.org/node/{abs(hash(name)) % 1000000}",
            "map_url": "https://www.openstreetmap.org/"}


def test_builds_requested_days_and_waits_for_approval(future_date):
    req = request(future_date)
    place_result = {"ok": True, "places": [place("Hill Park", "Park"), place("City Museum", "Museum", True)], "source": "test"}
    weather = {"ok": True, "forecast": [], "source": "test"}
    result = build_itinerary(req, place_result, weather)
    assert len(result["days"]) == req.days
    assert result["requires_human_approval"] is True
    assert result["approval_status"] == "Pending approval"
    assert result["generated_by"].startswith("Rule-based")
    assert all(not a.get("place_name") or a["place_name"] in {"Hill Park", "City Museum"}
               for day in result["days"] for a in day["activities"])


def test_budget_overrun_is_reported(future_date):
    req = request(future_date, budget_inr=1000)
    result = build_itinerary(req, {"ok": True, "places": [], "source": "test"}, {"ok": False, "forecast": []})
    assert any("exceed" in x.lower() for x in result["validation_issues"])


def test_transport_price_flows_to_budget(future_date):
    req = request(future_date, budget_inr=50000)
    result = build_itinerary(req, {"ok": True, "places": [], "source": "test"}, {"ok": False, "forecast": []})
    updated = apply_transport_option(result, req, {"mode": "Flight", "airline": "Test Air", "price": 8000})
    assert updated["cost_summary"]["transport_inr"] == 8000
    assert updated["cost_summary"]["total_estimated_inr"] >= 8000
    assert updated["requires_human_approval"] is True


def test_rain_replanning_switches_to_indoor_place(future_date):
    req = request(future_date)
    outdoor = place("Coastal Walk", "Park")
    indoor = place("Local Art Museum", "Museum", True)
    result = build_itinerary(req, {"ok": True, "places": [outdoor, indoor], "source": "test"}, {"ok": True, "forecast": []})
    revised = replan_from_feedback(result, "Rain is expected on Day 1; prefer indoor activities", req, [outdoor, indoor], {"ok": True, "forecast": []})
    assert revised["requires_human_approval"] is True
    assert revised["approval_status"] == "Revised draft — approval required"
    day1 = revised["days"][0]
    assert any("Museum" in str(a.get("place_name", "")) or "indoor" in a.get("activity", "").lower() for a in day1["activities"])
    assert revised["change_log"]


def test_slow_pace_replanning_reduces_activity_count(future_date):
    req = request(future_date)
    places = [place("Garden", "Park"), place("Museum", "Museum", True), place("Viewpoint", "Viewpoint")]
    result = build_itinerary(req, {"ok": True, "places": places, "source": "test"}, {"ok": False, "forecast": []})
    before = len(result["days"][0]["activities"])
    revised = replan_from_feedback(result, "make the pace slower and have fewer places", req, places)
    assert len(revised["days"][0]["activities"]) <= before
    assert revised["requires_human_approval"] is True


def test_numeric_budget_feedback_updates_constraint(future_date):
    req = request(future_date, budget_inr=30000)
    places = [place("Garden", "Park")]
    result = build_itinerary(req, {"ok": True, "places": places, "source": "test"}, {"ok": False, "forecast": []})
    revised = replan_from_feedback(result, "reduce the total budget to ₹20000", req, places)
    assert req.budget_inr == 20000
    assert revised["cost_summary"]["budget_inr"] == 20000
    assert revised["requires_human_approval"] is True


def test_budget_request_without_target_is_explained(future_date):
    req = request(future_date)
    result = build_itinerary(req, {"ok": True, "places": [place("Garden", "Park")], "source": "test"}, {"ok": False, "forecast": []})
    revised = replan_from_feedback(result, "please reduce the budget", req, [])
    assert "target amount" in revised.get("replan_error", "")


def test_missing_places_never_invents_named_attraction(future_date):
    req = request(future_date)
    result = build_itinerary(req, {"ok": False, "places": [], "source": "test"}, {"ok": False, "forecast": []})
    assert all(not a.get("place_name") for day in result["days"] for a in day["activities"])
    assert not any("Unverified place name" in x for x in validate_itinerary(result, req, []))
