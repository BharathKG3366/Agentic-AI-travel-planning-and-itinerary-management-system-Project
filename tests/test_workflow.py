from datetime import date, timedelta

from agents.planner import TripRequest
from agents.workflow import run_workflow


def test_workflow_runs_with_mocked_tools(monkeypatch):
    from agents import workflow

    future = date.today() + timedelta(days=8)
    req = TripRequest(origin_city="Bengaluru", destination="Mysuru", departure_date=future,
                      days=2, travelers=2, budget_inr=30000, interests=["nature"],
                      transport_mode="None")
    places = [{"name": "Mysuru Palace", "category": "Attraction", "indoor_hint": True,
               "osm_url": "https://www.openstreetmap.org/", "map_url": "https://www.openstreetmap.org/"},
              {"name": "Kukkarahalli Lake Park", "category": "Park", "indoor_hint": False,
               "osm_url": "https://www.openstreetmap.org/", "map_url": "https://www.openstreetmap.org/"}]
    monkeypatch.setattr(workflow, "search_places", lambda city: {"ok": True, "source": "test", "places": places, "message": "fixture"})
    monkeypatch.setattr(workflow, "get_weather", lambda city, start, end: {"ok": True, "source": "test", "forecast": [], "message": "fixture"})
    state = run_workflow(req)
    assert len(state["itinerary"]["days"]) == 2
    assert state["itinerary"]["requires_human_approval"] is True
    assert any(t["agent"] == "Goal Decomposition Agent" for t in state["trace"])
    assert any(t["agent"] == "Constraint Validation Agent" for t in state["trace"])
    assert state["itinerary"].get("trip_id") is not None
