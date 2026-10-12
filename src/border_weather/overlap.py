from __future__ import annotations

from pathlib import Path
import math
import pandas as pd


COMPARE_VARS = [
    "temperature",
    "dew_point_temperature",
    "relative_humidity",
    "wind_speed",
    "wind_direction",
    "wind_gust",
    "station_level_pressure",
    "sea_level_pressure",
]


def _load_station_series(
    observations_dir: str,
    site_key: str,
    source_station_id: str,
) -> pd.DataFrame:
    base = Path(observations_dir)

    files = sorted(
        base.glob(
            f"year=*/site_key={site_key}/"
            f"source_station_id={source_station_id}/"
            "observations.parquet"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"No observations found for {site_key} / {source_station_id}"
        )

    frames = [pd.read_parquet(file) for file in files]
    combined = pd.concat(frames, ignore_index=True)

    combined["timestamp_utc"] = pd.to_datetime(
        combined["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    combined = combined.dropna(subset=["timestamp_utc"])

    return combined


def _first_valid(series: pd.Series):
    values = series.dropna()
    if values.empty:
        return pd.NA
    return values.iloc[0]


def _collapse_to_hour(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reduce NOAA source reports into one diagnostic row per UTC clock hour.

    This does not alter the source archive. It is only used to compare
    overlapping station identifiers.
    """
    df = df.copy()

    df["hour_utc"] = df["timestamp_utc"].dt.floor("h")

    available_vars = [
        var for var in COMPARE_VARS
        if var in df.columns
    ]

    collapsed = (
        df.groupby("hour_utc", as_index=False)[available_vars]
        .agg(_first_valid)
        .sort_values("hour_utc")
    )

    return collapsed


def _circular_difference_deg(a, b):
    """
    Smallest angular difference between two directions.

    Example:
    359 vs 1 -> 2 degrees
    """
    try:
        a = float(a)
        b = float(b)
    except (TypeError, ValueError):
        return math.nan

    if pd.isna(a) or pd.isna(b):
        return math.nan

    # Ignore invalid/special direction codes outside 0..360.
    if not (0 <= a <= 360 and 0 <= b <= 360):
        return math.nan

    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def compare_station_ids_hourly(
    site_key: str,
    station_a: str,
    station_b: str,
    observations_dir: str = "data/processed/observations",
    output_dir: str = "reports/overlap",
) -> tuple[pd.DataFrame, pd.DataFrame]:

    a = _load_station_series(
        observations_dir,
        site_key,
        station_a,
    )

    b = _load_station_series(
        observations_dir,
        site_key,
        station_b,
    )

    a = _collapse_to_hour(a)
    b = _collapse_to_hour(b)

    merged = a.merge(
        b,
        on="hour_utc",
        how="outer",
        suffixes=("_a", "_b"),
        indicator=True,
    )

    shared_hours = int((merged["_merge"] == "both").sum())
    only_a = int((merged["_merge"] == "left_only").sum())
    only_b = int((merged["_merge"] == "right_only").sum())

    summary_rows = []

    for var in COMPARE_VARS:
        a_col = f"{var}_a"
        b_col = f"{var}_b"

        if a_col not in merged.columns or b_col not in merged.columns:
            continue

        both_mask = (
            merged[a_col].notna()
            & merged[b_col].notna()
        )

        both = merged.loc[both_mask].copy()

        values_only_a = int(
            (
                merged[a_col].notna()
                & merged[b_col].isna()
            ).sum()
        )

        values_only_b = int(
            (
                merged[b_col].notna()
                & merged[a_col].isna()
            ).sum()
        )

        n_both_values = len(both)

        mean_abs_diff = None
        median_abs_diff = None
        max_abs_diff = None
        exact_match_pct = None

        temp_gt_05 = None
        temp_gt_1 = None
        temp_gt_2 = None

        if n_both_values:
            if var == "wind_direction":
                differences = both.apply(
                    lambda row: _circular_difference_deg(
                        row[a_col],
                        row[b_col],
                    ),
                    axis=1,
                )

                differences = pd.to_numeric(
                    differences,
                    errors="coerce",
                ).dropna()

            else:
                a_num = pd.to_numeric(
                    both[a_col],
                    errors="coerce",
                )

                b_num = pd.to_numeric(
                    both[b_col],
                    errors="coerce",
                )

                valid = a_num.notna() & b_num.notna()

                differences = (
                    a_num[valid] - b_num[valid]
                ).abs()

            if not differences.empty:
                mean_abs_diff = float(differences.mean())
                median_abs_diff = float(differences.median())
                max_abs_diff = float(differences.max())

                if var == "temperature":
                    temp_gt_05 = int((differences > 0.5).sum())
                    temp_gt_1 = int((differences > 1.0).sum())
                    temp_gt_2 = int((differences > 2.0).sum())

            exact_match_pct = float(
                100
                * (
                    both[a_col].astype("string")
                    == both[b_col].astype("string")
                ).mean()
            )

        summary_rows.append(
            {
                "site_key": site_key,
                "station_a": station_a,
                "station_b": station_b,
                "variable": var,
                "shared_hours": shared_hours,
                "hours_only_a": only_a,
                "hours_only_b": only_b,
                "n_both_values": n_both_values,
                "values_only_a": values_only_a,
                "values_only_b": values_only_b,
                "exact_match_pct": exact_match_pct,
                "mean_abs_difference": mean_abs_diff,
                "median_abs_difference": median_abs_diff,
                "max_abs_difference": max_abs_diff,
                "temperature_diff_gt_0_5": temp_gt_05,
                "temperature_diff_gt_1": temp_gt_1,
                "temperature_diff_gt_2": temp_gt_2,
            }
        )

    summary = pd.DataFrame(summary_rows)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    stem = (
        f"{site_key}_{station_a}_vs_{station_b}_hourly"
    )

    summary.to_csv(
        out / f"{stem}_summary.csv",
        index=False,
    )

    summary.to_parquet(
        out / f"{stem}_summary.parquet",
        index=False,
    )

    merged.to_parquet(
        out / f"{stem}_hours.parquet",
        index=False,
    )

    # Save temperature outliers for direct inspection.
    temp_a = "temperature_a"
    temp_b = "temperature_b"

    if temp_a in merged.columns and temp_b in merged.columns:
        outliers = merged[
            merged[temp_a].notna()
            & merged[temp_b].notna()
        ].copy()

        outliers["temperature_abs_difference"] = (
            pd.to_numeric(outliers[temp_a], errors="coerce")
            - pd.to_numeric(outliers[temp_b], errors="coerce")
        ).abs()

        outliers = outliers[
            outliers["temperature_abs_difference"] > 2.0
        ].sort_values(
            "temperature_abs_difference",
            ascending=False,
        )

        outliers.to_csv(
            out / f"{stem}_temperature_outliers.csv",
            index=False,
        )

    return summary, merged