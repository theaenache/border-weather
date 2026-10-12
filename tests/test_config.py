from border_weather.config import load_stations


def test_nine_sites():
    stations = load_stations()
    assert len(stations) == 9
    assert {s.site_key for s in stations} >= {"mcallen", "brownsville", "yuma", "imperial"}
