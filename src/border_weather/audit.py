from __future__ import annotations

from pathlib import Path
import pandas as pd

VARS = [
    "temperature",
    "dew_point_temperature",
    "relative_humidity",
    "wind_speed",
    "wind_direction",
    "wind_gust",
    "station_level_pressure",
    "sea_level_pressure",
    "visibility",
    "wet_bulb_temperature",
    "precipitation",
    "precipitation_1_hour",
    "precipitation_3_hour",
    "precipitation_6_hour",
    "precipitation_24_hour",
]


def _expected_hours_for_year(
    year: int,
    latest_timestamp: pd.Timestamp,
) -> int:
    """
    Count expected hourly slots.

    For completed years, use the full calendar year.
    For the current year, only count through the latest observed hour so
    future hours are not treated as missing.
    """
    start = pd.Timestamp(f"{year}-01-01T00:00:00Z")
    next_year = pd.Timestamp(f"{year + 1}-01-01T00:00:00Z")

    now_utc = pd.Timestamp.now(tz="UTC")

    if year < now_utc.year:
        end = next_year
    else:
        latest_hour = pd.to_datetime(latest_timestamp, utc=True).floor("h")
        end = min(latest_hour + pd.Timedelta(hours=1), next_year)

    expected = int((end - start).total_seconds() // 3600)
    return max(expected, 0)


def _hourly_metrics(
    df: pd.DataFrame,
    variable: str,
    year: int,
) -> dict:
    if variable not in df.columns:
        return {
            "n_non_null": 0,
            "record_presence_pct": 0.0,
            "expected_hours": 0,
            "hours_with_observation": 0,
            "hourly_coverage_pct": 0.0,
            "median_reports_per_observed_hour": 0.0,
            "max_gap_hours": None,
        }

    s = df[variable]
    n_non_null = int(s.notna().sum())

    record_presence_pct = (
        float(100 * s.notna().mean()) if len(s) else 0.0
    )

    valid = df.loc[s.notna(), ["timestamp_utc"]].copy()

    if valid.empty:
        latest_timestamp = df["timestamp_utc"].max()
        expected_hours = (
            _expected_hours_for_year(year, latest_timestamp)
            if pd.notna(latest_timestamp)
            else 0
        )

        return {
            "n_non_null": n_non_null,
            "record_presence_pct": record_presence_pct,
            "expected_hours": expected_hours,
            "hours_with_observation": 0,
            "hourly_coverage_pct": 0.0,
            "median_reports_per_observed_hour": 0.0,
            "max_gap_hours": None,
        }

    valid["timestamp_utc"] = pd.to_datetime(
        valid["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    valid = valid.dropna(subset=["timestamp_utc"])

    if valid.empty:
        return {
            "n_non_null": n_non_null,
            "record_presence_pct": record_presence_pct,
            "expected_hours": 0,
            "hours_with_observation": 0,
            "hourly_coverage_pct": 0.0,
            "median_reports_per_observed_hour": 0.0,
            "max_gap_hours": None,
        }

    valid["hour"] = valid["timestamp_utc"].dt.floor("h")

    hourly_counts = valid.groupby("hour").size().sort_index()

    hours_with_observation = int(hourly_counts.index.nunique())

    latest_timestamp = df["timestamp_utc"].max()
    expected_hours = _expected_hours_for_year(
        year,
        latest_timestamp,
    )

    hourly_coverage_pct = (
        float(100 * hours_with_observation / expected_hours)
        if expected_hours
        else 0.0
    )

    median_reports_per_observed_hour = float(hourly_counts.median())

    if len(hourly_counts.index) > 1:
        gaps = (
            hourly_counts.index.to_series()
            .diff()
            .dropna()
            .dt.total_seconds()
            .div(3600)
        )

        # Convert spacing between observed hours into number of missing hours.
        missing_gaps = (gaps - 1).clip(lower=0)

        max_gap_hours = (
            float(missing_gaps.max())
            if not missing_gaps.empty
            else 0.0
        )
    else:
        max_gap_hours = None

    return {
        "n_non_null": n_non_null,
        "record_presence_pct": record_presence_pct,
        "expected_hours": expected_hours,
        "hours_with_observation": hours_with_observation,
        "hourly_coverage_pct": hourly_coverage_pct,
        "median_reports_per_observed_hour": (
            median_reports_per_observed_hour
        ),
        "max_gap_hours": max_gap_hours,
    }


def build_audit(
    observations_dir: str = "data/processed/observations",
    output_dir: str = "reports/audit",
) -> pd.DataFrame:
    files = list(
        Path(observations_dir).glob(
            "year=*/site_key=*/source_station_id=*/observations.parquet"
        )
    )

    rows = []

    for f in files:
        df = pd.read_parquet(f)

        if df.empty:
            continue

        df["timestamp_utc"] = pd.to_datetime(
            df["timestamp_utc"],
            utc=True,
            errors="coerce",
        )

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
            metrics = _hourly_metrics(
                df=df,
                variable=var,
                year=year,
            )

            row = base | {
                "variable": var,
                **metrics,
            }

            rows.append(row)

    audit = pd.DataFrame(rows)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    audit.to_parquet(
        out / "station_variable_year.parquet",
        index=False,
    )

    audit.to_csv(
        out / "station_variable_year.csv",
        index=False,
    )

    return audit