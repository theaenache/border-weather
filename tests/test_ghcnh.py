from pathlib import Path
from border_weather.ghcnh import year_url, parse_psv


def test_year_url():
    assert year_url("USW00012959", 2000).endswith("/2000/psv/GHCNh_USW00012959_2000.psv")


def test_schema_tolerant_parser(tmp_path: Path):
    p = tmp_path / "sample.psv"
    p.write_text(
        "STATION|DATE|Temperature|Dew Point Temperature|Wind Speed|Wind Direction|Precipitation\n"
        "USW00012959|2024-01-01T00:00:00|20.0|10.0|3.0|180|0.0\n",
        encoding="utf-8",
    )
    canonical, raw = parse_psv(p)
    assert len(raw) == 1
    assert canonical.loc[0, "station"] == "USW00012959"
    assert canonical.loc[0, "temperature"] == 20.0
    assert str(canonical.loc[0, "timestamp_utc"]) == "2024-01-01 00:00:00+00:00"
