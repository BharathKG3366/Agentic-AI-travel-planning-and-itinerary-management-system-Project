from agents.memory import list_trips, load_profile, save_profile, save_trip


def test_local_profile_and_trip_persist():
    save_profile({"destination": "Kochi", "interests": ["nature"]})
    assert load_profile()["destination"] == "Kochi"
    trip_id = save_trip({"origin_city": "Bengaluru", "destination": "Kochi"}, {"approval_status": "Pending approval", "cost_summary": {"total_estimated_inr": 1000}})
    trips = list_trips()
    assert any(t["id"] == trip_id and t["title"] == "Bengaluru → Kochi" for t in trips)
