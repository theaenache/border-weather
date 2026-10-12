from __future__ import annotations
import hashlib
import io
from pathlib import Path
import requests
import pandas as pd

DEFAULT_BASE = "https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/access/by-year"

# NOAA has changed capitalization/labels across product revisions and derived search views.
# Normalize common variants without requiring the whole 329-column schema to be frozen here.
ALIASES = {
    "station": ["STATION", "Station_ID", "station"],
    "date": ["DATE", "date"],
    "latitude": ["LATITUDE", "Latitude", "latitude"],
    "longitude": ["LONGITUDE", "Longitude", "longitude"],
    "elevation_m": ["ELEVATION", "Elevation", "elevation"],
    "temperature": ["Temperature", "temperature", "TEMPERATURE"],
    "dew_point_temperature": ["Dew Point Temperature", "dew_point_temperature", "DEW_POINT_TEMPERATURE"],
    "relative_humidity": ["Relative Humidity", "relative_humidity", "RELATIVE_HUMIDITY"],
    "wind_direction": ["Wind Direction", "wind_direction", "WIND_DIRECTION"],
    "wind_speed": ["Wind Speed", "wind_speed", "WIND_SPEED"],
    "wind_gust": ["Wind Gust", "wind_gust", "WIND_GUST"],
    "station_level_pressure": ["Station Level Pressure", "station_level_pressure", "STATION_LEVEL_PRESSURE"],
    "sea_level_pressure": ["Sea Level Pressure", "sea_level_pressure", "SEA_LEVEL_PRESSURE"],
    "visibility": ["Visibility", "visibility", "VISIBILITY"],
    "wet_bulb_temperature": ["Wet Bulb Temperature", "wet_bulb_temperature", "WET_BULB_TEMPERATURE"],
    "precipitation": ["Precipitation", "precipitation", "PRECIPITATION"],
    "precipitation_1_hour": ["precipitation_1_hour", "Precipitation 1 Hour"],
    "precipitation_3_hour": ["precipitation_3_hour", "Precipitation 3 Hour"],
    "precipitation_6_hour": ["precipitation_6_hour", "Precipitation 6 Hour"],
    "precipitation_24_hour": ["precipitation_24_hour", "Precipitation 24 Hour"],
}


def year_url(station_id: str, year: int, base_url: str = DEFAULT_BASE) -> str:
    return f"{base_url}/{year}/psv/GHCNh_{station_id}_{year}.psv"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_year(station_id: str, year: int, dest: Path, base_url: str = DEFAULT_BASE, timeout: int = 90) -> tuple[Path, str]:
    url = year_url(station_id, year, base_url)
    response = requests.get(url, timeout=timeout)
    if response.status_code == 404:
        raise FileNotFoundError(url)
    response.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
    return dest, sha256_bytes(response.content)


def _first_col(df: pd.DataFrame, names: list[str]) -> pd.Series:
    for name in names:
        if name in df.columns:
            return df[name]
    return pd.Series(pd.NA, index=df.index, dtype="object")


def parse_psv(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (canonical_subset, complete_raw_table).

    The complete NOAA row is preserved separately. Canonical extraction is deliberately
    tolerant to header-name changes. Numeric units remain exactly as supplied by GHCNh;
    no meteorological values are inferred or filled.
    """
    raw = pd.read_csv(path, sep="|", low_memory=False)
    out = pd.DataFrame(index=raw.index)
    for target, candidates in ALIASES.items():
        out[target] = _first_col(raw, candidates)
    out["timestamp_utc"] = pd.to_datetime(out["date"], utc=True, errors="coerce")
    out["source_row_number"] = range(1, len(out) + 1)
    out["source_file"] = Path(path).name
    return out, raw
