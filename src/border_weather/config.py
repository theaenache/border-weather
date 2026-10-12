from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass(frozen=True)
class StationIdentifier:
    ghcnh_id: str
    role: str
    verify: bool = False

@dataclass(frozen=True)
class Station:
    site_key: str
    station_name: str
    county: str
    county_fips: str
    state: str
    timezone: str
    tier: str
    identifiers: tuple[StationIdentifier, ...]


def load_yaml(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_stations(path: str | Path = "config/stations.yml") -> list[Station]:
    obj = load_yaml(path)
    out = []
    for s in obj["stations"]:
        ids = tuple(StationIdentifier(**i) for i in s["identifiers"])
        out.append(Station(identifiers=ids, **{k: v for k, v in s.items() if k != "identifiers"}))
    return out
