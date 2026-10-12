from __future__ import annotations
from pathlib import Path
import pandas as pd

VARS = [
    "temperature", "dew_point_temperature", "relative_humidity",
    "wind_speed", "wind_direction", "wind_gust",
    "station_level_pressure", "sea_level_pressure", "visibility",
    "wet_bulb_temperature", "precipitation", "precipitation_1_hour",
    "precipitation_3_hour", "precipitation_6_hour", "precipitation_24_hour",
]


def build_audit(observations_dir: str = "data/processed/observations", output_dir: str = "reports/audit") -> pd.DataFrame:
    files = list(Path(observations_dir).glob("year=*/site_key=*/source_station_id=*/observations.parquet"))
    rows = []
    for f in files:
        df = pd.read_parquet(f)
        if df.empty:
            continue
        year = int(f.parts[-4].split("=")[1])
        base = {
            "site_key": df["site_key"].iloc[0],
            "source_station_id": df["source_station_id"].iloc[0],
            "year": year,
            "n_source_records": len(df),
            "first_observation": df["timestamp_utc"].min(),
            "last_observation": df["timestamp_utc"].max(),
        }
        for var in VARS:
            s = df[var] if var in df else pd.Series(dtype="object")
            row = base | {
                "variable": var,
                "n_non_null": int(s.notna().sum()),
                "record_presence_pct": float(100 * s.notna().mean()) if len(s) else 0.0,
            }
            rows.append(row)
    audit = pd.DataFrame(rows)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit.to_parquet(out / "station_variable_year.parquet", index=False)
    audit.to_csv(out / "station_variable_year.csv", index=False)
    return audit
