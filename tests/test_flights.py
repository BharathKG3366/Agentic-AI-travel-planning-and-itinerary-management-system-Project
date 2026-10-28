from datetime import date

from providers.flights import _normalise


def test_normalize_serpapi_result():
    item = {
        "flights": [{
            "airline": "Example Air",
            "departure_airport": {"id": "BLR", "time": "2027-02-01 07:15"},
            "arrival_airport": {"id": "DEL", "time": "2027-02-01 10:05"},
        }],
        "total_duration": 170,
        "price": 5240,
    }
    result = _normalise(item, "BLR", "DEL", date(2027, 2, 1), None)
    assert result["airline"] == "Example Air"
    assert result["origin"] == "BLR"
    assert result["destination"] == "DEL"
    assert result["price"] == 5240.0
    assert result["currency"] == "INR"
    assert result["stops"] == 0
    assert result["duration"] == "2h 50m"


def test_normalize_handles_missing_price():
    result = _normalise({"flights": []}, "BLR", "DEL", date(2027, 2, 1), None)
    assert result["price"] is None
    assert result["airline"] == "Airline not supplied"
