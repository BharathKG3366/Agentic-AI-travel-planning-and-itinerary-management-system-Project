from providers.weather import WMO_CODES


def test_weather_codes_have_readable_labels():
    assert WMO_CODES[0] == "Clear sky"
    assert "rain" in WMO_CODES[61].lower()
    assert "thunderstorm" in WMO_CODES[95].lower()
