from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import pandas as pd

from .config import load_stations, load_yaml
from .ghcnh import download_year, parse_psv


def _row_hash(df: pd.DataFrame) -> pd.Series:
    # Stable lineage hash over canonical source-derived values; not used to invent uniqueness.
    cols = [c for c in df.columns if c not in {"source_row_hash"}]
    return df[cols].astype("string").fillna("<NA>").agg("|".join, axis=1).map(
        lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
    )


def ingest_station_year(site, identifier, year: int, settings: dict, force: bool = True) -> dict:
    raw_dir = Path(settings["storage"]["raw_dir"]) / identifier.ghcnh_id
    raw_path = raw_dir / f"GHCNh_{identifier.ghcnh_id}_{year}.psv"
    raw_path, digest = download_year(identifier.ghcnh_id, year, raw_path, settings["source"]["base_url"])
    canonical, raw = parse_psv(raw_path)
    canonical.insert(0, "site_key", site.site_key)
    canonical.insert(1, "source_station_id", identifier.ghcnh_id)
    canonical.insert(2, "county", site.county)
    canonical.insert(3, "county_fips", site.county_fips)
    canonical.insert(4, "state", site.state)
    canonical.insert(5, "timezone", site.timezone)
    canonical["identifier_role"] = identifier.role
    canonical["source_row_hash"] = _row_hash(canonical)

    out = Path(settings["storage"]["observations_dir"]) / f"year={year}" / f"site_key={site.site_key}" / f"source_station_id={identifier.ghcnh_id}" / "observations.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    canonical.to_parquet(out, index=False)

    # Preserve all NOAA columns as a compressed Parquet mirror next to raw PSV.
    raw_parquet = raw_path.with_suffix(".raw.parquet")
    raw.to_parquet(raw_parquet, index=False)

    return {
        "site_key": site.site_key,
        "source_station_id": identifier.ghcnh_id,
        "year": year,
        "source_sha256": digest,
        "rows": len(canonical),
        "first_timestamp": canonical["timestamp_utc"].min(),
        "last_timestamp": canonical["timestamp_utc"].max(),
        "ingested_at_utc": datetime.now(timezone.utc),
        "status": "ok",
        "raw_path": str(raw_path),
        "processed_path": str(out),
    }


def save_manifest(records: list[dict], settings: dict) -> None:
    path = Path(settings["storage"]["manifest_file"])
    path.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame(records)
    if path.exists():
        old = pd.read_parquet(path)
        combined = pd.concat([old, new], ignore_index=True)
        combined = combined.sort_values("ingested_at_utc").drop_duplicates(
            ["site_key", "source_station_id", "year"], keep="last"
        )
    else:
        combined = new
    combined.to_parquet(path, index=False)


def backfill(start_year: int, end_year: int, station_filter: set[str] | None = None) -> pd.DataFrame:
    settings = load_yaml("config/settings.yml")
    records = []
    for site in load_stations():
        if station_filter and site.site_key not in station_filter:
            continue
        for ident in site.identifiers:
            for year in range(start_year, end_year + 1):
                try:
                    rec = ingest_station_year(site, ident, year, settings)
                except FileNotFoundError:
                    rec = {"site_key": site.site_key, "source_station_id": ident.ghcnh_id, "year": year, "status": "not_found", "ingested_at_utc": datetime.now(timezone.utc)}
                except Exception as exc:
                    rec = {"site_key": site.site_key, "source_station_id": ident.ghcnh_id, "year": year, "status": f"error:{type(exc).__name__}:{exc}", "ingested_at_utc": datetime.now(timezone.utc)}
                records.append(rec)
                print(f"{site.site_key} {ident.ghcnh_id} {year}: {rec['status']}")
    save_manifest(records, settings)
    return pd.DataFrame(records)


def update_current_year() -> pd.DataFrame:
    year = datetime.now(timezone.utc).year
    return backfill(year, year)
