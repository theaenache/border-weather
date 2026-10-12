from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd


NUMERIC_VARS = [
    "temperature",
    "dew_point_temperature",
    "relative_humidity",
    "wind_speed",
    "wind_gust",
    "station_level_pressure",
    "sea_level_pressure",
    "visibility",
    "wet_bulb_temperature",
]


def _circular_mean_deg(values: pd.Series) -> float | None:
    s = pd.to_numeric(values, errors="coerce")
    s = s[(s >= 0) & (s <= 360)].dropna()

    if s.empty:
        return None

    radians = np.deg2rad(s.to_numpy())

    mean_sin = np.sin(radians).mean()
    mean_cos = np.cos(radians).mean()

    if np.isclose(mean_sin, 0) and np.isclose(mean_cos, 0):
        return None

    direction = math.degrees(
        math.atan2(mean_sin, mean_cos)
    )

    return float(direction % 360)


def _metadata_columns(df: pd.DataFrame) -> list[str]:
    candidates = [
        "site_key",
        "source_station_id",
        "county",
        "county_fips",
        "state",
        "timezone",
        "identifier_role",
    ]

    return [
        col
        for col in candidates
        if col in df.columns
    ]


def _parse_partition_value(
    path: Path,
    prefix: str,
) -> str:
    for part in path.parts:
        if part.startswith(prefix):
            return part.split("=", 1)[1]

    raise ValueError(
        f"Could not find partition {prefix} in {path}"
    )


def _build_hourly_from_file(
    input_path: Path,
) -> pd.DataFrame:

    df = pd.read_parquet(input_path)

    if df.empty:
        return pd.DataFrame()

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    df = df.dropna(
        subset=["timestamp_utc"]
    )

    if df.empty:
        return pd.DataFrame()

    df["hour_utc"] = (
        df["timestamp_utc"]
        .dt.floor("h")
    )

    metadata_cols = _metadata_columns(df)

    rows = []

    for hour_utc, group in df.groupby(
        "hour_utc",
        sort=True,
    ):
        row = {
            "hour_utc": hour_utc,
            "n_source_records": len(group),
        }

        for col in metadata_cols:
            row[col] = group[col].iloc[0]

        for var in NUMERIC_VARS:
            if var not in group.columns:
                continue

            values = pd.to_numeric(
                group[var],
                errors="coerce",
            ).dropna()

            row[f"{var}_n"] = int(
                len(values)
            )

            if values.empty:
                row[f"{var}_mean"] = None
                row[f"{var}_min"] = None
                row[f"{var}_max"] = None
            else:
                row[f"{var}_mean"] = float(
                    values.mean()
                )

                row[f"{var}_min"] = float(
                    values.min()
                )

                row[f"{var}_max"] = float(
                    values.max()
                )

        if "wind_direction" in group.columns:
            wind_dir = pd.to_numeric(
                group["wind_direction"],
                errors="coerce",
            )

            row["wind_direction_n"] = int(
                wind_dir.notna().sum()
            )

            row[
                "wind_direction_circular_mean"
            ] = _circular_mean_deg(
                wind_dir
            )

        rows.append(row)

    return pd.DataFrame(rows)


def build_hourly_partitions(
    observations_dir: str = (
        "data/processed/observations"
    ),
    output_dir: str = (
        "data/processed/summaries/hourly"
    ),
) -> int:

    input_root = Path(observations_dir)
    output_root = Path(output_dir)

    files = sorted(
        input_root.glob(
            "year=*/site_key=*/"
            "source_station_id=*/"
            "observations.parquet"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"No observations found under "
            f"{observations_dir}"
        )

    files_written = 0

    for input_path in files:
        year = _parse_partition_value(
            input_path,
            "year=",
        )

        site_key = _parse_partition_value(
            input_path,
            "site_key=",
        )

        source_station_id = (
            _parse_partition_value(
                input_path,
                "source_station_id=",
            )
        )

        hourly = _build_hourly_from_file(
            input_path
        )

        if hourly.empty:
            continue

        out_path = (
            output_root
            / f"year={year}"
            / f"site_key={site_key}"
            / (
                "source_station_id="
                f"{source_station_id}"
            )
            / "hourly.parquet"
        )

        out_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        hourly.to_parquet(
            out_path,
            index=False,
        )

        files_written += 1

        print(
            f"hourly {site_key} "
            f"{source_station_id} "
            f"{year}: {len(hourly):,} rows"
        )

    return files_written


def _add_local_period_columns(
    hourly: pd.DataFrame,
) -> pd.DataFrame:

    if hourly.empty:
        return hourly

    if "timezone" not in hourly.columns:
        raise ValueError(
            "Hourly data is missing timezone."
        )

    frames = []

    for timezone_name, group in hourly.groupby(
        "timezone",
        dropna=False,
    ):
        if pd.isna(timezone_name):
            raise ValueError(
                "Missing timezone metadata."
            )

        group = group.copy()

        group["hour_utc"] = pd.to_datetime(
            group["hour_utc"],
            utc=True,
            errors="coerce",
        )

        local = (
            group["hour_utc"]
            .dt.tz_convert(
                str(timezone_name)
            )
        )

        group["local_date"] = (
            local.dt.date
        )

        group["week_start_local"] = (
            local.dt.normalize()
            - pd.to_timedelta(
                local.dt.weekday,
                unit="D",
            )
        ).dt.date

        group["month_start_local"] = (
            local.dt.strftime(
                "%Y-%m-01"
            )
        )

        frames.append(group)

    return pd.concat(
        frames,
        ignore_index=True,
    )


def _aggregate_period(
    hourly: pd.DataFrame,
    period_column: str,
) -> pd.DataFrame:

    metadata_cols = _metadata_columns(
        hourly
    )

    group_cols = (
        metadata_cols
        + [period_column]
    )

    rows = []

    for keys, group in hourly.groupby(
        group_cols,
        dropna=False,
        sort=True,
    ):
        if not isinstance(keys, tuple):
            keys = (keys,)

        row = dict(
            zip(group_cols, keys)
        )

        row[
            "n_hours_with_any_source_record"
        ] = int(
            group["hour_utc"].nunique()
        )

        for var in NUMERIC_VARS:
            mean_col = f"{var}_mean"
            min_col = f"{var}_min"
            max_col = f"{var}_max"
            n_col = f"{var}_n"

            if mean_col not in group.columns:
                continue

            means = pd.to_numeric(
                group[mean_col],
                errors="coerce",
            ).dropna()

            mins = pd.to_numeric(
                group[min_col],
                errors="coerce",
            ).dropna()

            maxs = pd.to_numeric(
                group[max_col],
                errors="coerce",
            ).dropna()

            counts = pd.to_numeric(
                group[n_col],
                errors="coerce",
            ).fillna(0)

            row[
                f"{var}_hours"
            ] = int(
                (counts > 0).sum()
            )

            row[
                f"{var}_mean"
            ] = (
                float(means.mean())
                if not means.empty
                else None
            )

            row[
                f"{var}_min"
            ] = (
                float(mins.min())
                if not mins.empty
                else None
            )

            row[
                f"{var}_max"
            ] = (
                float(maxs.max())
                if not maxs.empty
                else None
            )

        direction_col = (
            "wind_direction_"
            "circular_mean"
        )

        if direction_col in group.columns:
            directions = group[
                direction_col
            ]

            row[
                "wind_direction_hours"
            ] = int(
                directions.notna().sum()
            )

            row[
                "wind_direction_"
                "circular_mean"
            ] = _circular_mean_deg(
                directions
            )

        rows.append(row)

    return pd.DataFrame(rows)


def _build_period_partitions(
    hourly_dir: str,
    output_dir: str,
    period: str,
) -> int:

    input_root = Path(hourly_dir)
    output_root = Path(output_dir)

    files = sorted(
        input_root.glob(
            "year=*/site_key=*/"
            "source_station_id=*/"
            "hourly.parquet"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"No hourly partitions under "
            f"{hourly_dir}"
        )

    files_written = 0

    for input_path in files:
        year = _parse_partition_value(
            input_path,
            "year=",
        )

        site_key = _parse_partition_value(
            input_path,
            "site_key=",
        )

        source_station_id = (
            _parse_partition_value(
                input_path,
                "source_station_id=",
            )
        )

        hourly = pd.read_parquet(
            input_path
        )

        if hourly.empty:
            continue

        hourly["hour_utc"] = (
            pd.to_datetime(
                hourly["hour_utc"],
                utc=True,
                errors="coerce",
            )
        )

        hourly = (
            _add_local_period_columns(
                hourly
            )
        )

        if period == "daily":
            period_column = "local_date"

        elif period == "weekly":
            period_column = (
                "week_start_local"
            )

        elif period == "monthly":
            period_column = (
                "month_start_local"
            )

        else:
            raise ValueError(
                f"Unknown period: {period}"
            )

        result = _aggregate_period(
            hourly,
            period_column,
        )

        if result.empty:
            continue

        out_path = (
            output_root
            / f"year={year}"
            / f"site_key={site_key}"
            / (
                "source_station_id="
                f"{source_station_id}"
            )
            / f"{period}.parquet"
        )

        out_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        result.to_parquet(
            out_path,
            index=False,
        )

        files_written += 1

        print(
            f"{period} {site_key} "
            f"{source_station_id} "
            f"{year}: "
            f"{len(result):,} rows"
        )

    return files_written


def build_daily_partitions(
    hourly_dir: str = (
        "data/processed/summaries/hourly"
    ),
    output_dir: str = (
        "data/processed/summaries/daily"
    ),
) -> int:

    return _build_period_partitions(
        hourly_dir=hourly_dir,
        output_dir=output_dir,
        period="daily",
    )


def build_weekly_partitions(
    hourly_dir: str = (
        "data/processed/summaries/hourly"
    ),
    output_dir: str = (
        "data/processed/summaries/weekly"
    ),
) -> int:

    return _build_period_partitions(
        hourly_dir=hourly_dir,
        output_dir=output_dir,
        period="weekly",
    )


def build_monthly_partitions(
    hourly_dir: str = (
        "data/processed/summaries/hourly"
    ),
    output_dir: str = (
        "data/processed/summaries/monthly"
    ),
) -> int:

    return _build_period_partitions(
        hourly_dir=hourly_dir,
        output_dir=output_dir,
        period="monthly",
    )


def build_all_summaries() -> dict[str, int]:

    hourly_files = (
        build_hourly_partitions()
    )

    daily_files = (
        build_daily_partitions()
    )

    weekly_files = (
        build_weekly_partitions()
    )

    monthly_files = (
        build_monthly_partitions()
    )

    return {
        "hourly_partitions": hourly_files,
        "daily_partitions": daily_files,
        "weekly_partitions": weekly_files,
        "monthly_partitions": monthly_files,
    }