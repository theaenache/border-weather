from __future__ import annotations

from pathlib import Path
import shutil

import duckdb


SUMMARY_LEVELS = [
    "hourly",
    "daily",
    "weekly",
    "monthly",
]


def _sql_path(path: Path | str) -> str:
    """Convert a path to a DuckDB-safe SQL string."""
    return str(path).replace("\\", "/").replace("'", "''")


def _summary_glob(level: str) -> str:
    return (
        f"data/processed/summaries/{level}/"
        "year=*/site_key=*/source_station_id=*/*.parquet"
    )


def _write_release_readme(
    path: Path,
    version: str,
) -> None:
    text = f"""# Border Weather Dataset {version}

## Overview

This release contains observed NOAA/NWS weather measurements and
derived temporal summaries for selected weather-station source streams
in border counties in Texas, Arizona, and California.

The project is designed around source fidelity:

- observed measurements only
- no interpolation
- no weather prediction or modeled filling
- missing observations remain missing
- parallel NOAA station/source identifiers remain separate
- source_station_id is retained throughout the dataset
- UTC timestamps are preserved for hourly data
- daily, weekly, and monthly summaries use each station's local timezone
- wind direction uses circular averaging

## Files

### station_metadata.csv

Station/source metadata for every source stream represented in the
release.

### station_variable_year_audit.csv

Human-readable station-variable-year completeness audit.

Important fields include:

- expected_hours
- hours_with_observation
- hourly_coverage_pct
- median_reports_per_observed_hour
- max_gap_hours

### station_variable_year_audit.parquet

Parquet version of the audit table.

### hourly.parquet

Hourly summaries generated from the canonical NOAA observations.

Multiple NOAA reports within the same hour are summarized without
merging different source_station_id streams.

### daily.parquet

Local-calendar daily summaries.

### weekly.parquet

Local-calendar weekly summaries.

### monthly.parquet

Local-calendar monthly summaries.

### border_weather.duckdb

Optional standalone DuckDB database containing:

- station_metadata
- station_audit
- hourly
- daily
- weekly
- monthly

The DuckDB file is distributed separately from the main data ZIP.

## Important limitation: precipitation

Precipitation observations remain preserved in the underlying canonical
NOAA dataset, but precipitation totals are not yet included in the
{version} summary release.

NOAA precipitation reports can represent overlapping accumulation
periods. A dedicated precipitation aggregation method is being developed
to avoid double-counting or creating synthetic measurements.

## Source streams

A physical weather site may have more than one NOAA source identifier.

These source streams are intentionally NOT merged automatically.

Analysts should use `source_station_id` when grouping, filtering, or
comparing observations.

## Missing data

Missing observations are retained as missing.

A missing value should not be interpreted as zero.

Use the station-variable-year audit table to evaluate temporal coverage
before analysis.

## Time aggregation

Hourly summaries are organized using UTC timestamps.

Daily, weekly, and monthly summaries are based on the station's local
timezone.

Because the underlying hourly archive is partitioned by UTC year, local
calendar periods near year boundaries may require additional care in
future releases.

## Reproducibility

The source code used to ingest, audit, and summarize the data is
maintained in the border-weather GitHub repository.

Release version: {version}
"""

    path.write_text(
        text,
        encoding="utf-8",
    )


def build_release(
    version: str = "v0.1",
    output_root: str = "releases",
) -> Path:

    release_name = f"border-weather-{version}"

    output_root_path = Path(output_root)
    release_dir = output_root_path / release_name

    # Remove an existing release directory so each build is reproducible.
    if release_dir.exists():
        shutil.rmtree(release_dir)

    release_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    con = duckdb.connect()

    try:
        # ---------------------------------------------------------
        # Build consolidated summary Parquet files
        # ---------------------------------------------------------

        for level in SUMMARY_LEVELS:
            source_glob = _sql_path(
                _summary_glob(level)
            )

            output_file = _sql_path(
                release_dir / f"{level}.parquet"
            )

            print(
                f"Building {level}.parquet ..."
            )

            con.execute(
                f"""
                COPY (
                    SELECT *
                    FROM read_parquet(
                        '{source_glob}',
                        hive_partitioning = false,
                        union_by_name = true
                    )
                )
                TO '{output_file}'
                (
                    FORMAT PARQUET,
                    COMPRESSION ZSTD
                )
                """
            )

        # ---------------------------------------------------------
        # Build station metadata from the consolidated hourly file
        # ---------------------------------------------------------

        hourly_file = _sql_path(
            release_dir / "hourly.parquet"
        )

        metadata_csv = _sql_path(
            release_dir / "station_metadata.csv"
        )

        print(
            "Building station_metadata.csv ..."
        )

        con.execute(
            f"""
            COPY (
                SELECT DISTINCT
                    site_key,
                    source_station_id,
                    county,
                    county_fips,
                    state,
                    timezone,
                    identifier_role
                FROM read_parquet(
                    '{hourly_file}'
                )
                ORDER BY
                    state,
                    county,
                    site_key,
                    source_station_id
            )
            TO '{metadata_csv}'
            (
                HEADER,
                DELIMITER ','
            )
            """
        )

        # ---------------------------------------------------------
        # Copy audit outputs
        # ---------------------------------------------------------

        audit_csv = Path(
            "reports/audit/"
            "station_variable_year.csv"
        )

        audit_parquet = Path(
            "reports/audit/"
            "station_variable_year.parquet"
        )

        if not audit_csv.exists():
            raise FileNotFoundError(
                f"Missing audit file: {audit_csv}"
            )

        if not audit_parquet.exists():
            raise FileNotFoundError(
                f"Missing audit file: {audit_parquet}"
            )

        print(
            "Copying audit files ..."
        )

        shutil.copy2(
            audit_csv,
            release_dir
            / "station_variable_year_audit.csv",
        )

        shutil.copy2(
            audit_parquet,
            release_dir
            / "station_variable_year_audit.parquet",
        )

    finally:
        con.close()

    # -------------------------------------------------------------
    # Write release README
    # -------------------------------------------------------------

    print(
        "Writing README.md ..."
    )

    _write_release_readme(
        release_dir / "README.md",
        version,
    )

    # -------------------------------------------------------------
    # Build standalone DuckDB database
    # -------------------------------------------------------------

    db_path = (
        release_dir
        / "border_weather.duckdb"
    )

    print(
        "Building border_weather.duckdb ..."
    )

    db = duckdb.connect(
        str(db_path)
    )

    try:
        for level in SUMMARY_LEVELS:
            parquet_file = _sql_path(
                release_dir
                / f"{level}.parquet"
            )

            db.execute(
                f"""
                CREATE TABLE {level} AS
                SELECT *
                FROM read_parquet(
                    '{parquet_file}'
                )
                """
            )

        metadata_path = _sql_path(
            release_dir
            / "station_metadata.csv"
        )

        db.execute(
            f"""
            CREATE TABLE station_metadata AS
            SELECT *
            FROM read_csv_auto(
                '{metadata_path}',
                header = true
            )
            """
        )

        audit_path = _sql_path(
            release_dir
            / "station_variable_year_audit.parquet"
        )

        db.execute(
            f"""
            CREATE TABLE station_audit AS
            SELECT *
            FROM read_parquet(
                '{audit_path}'
            )
            """
        )

        db.execute(
            """
            CREATE INDEX idx_hourly_station
            ON hourly(
                site_key,
                source_station_id,
                hour_utc
            )
            """
        )

    finally:
        db.close()

    # -------------------------------------------------------------
    # Build lightweight ZIP without the DuckDB file
    # -------------------------------------------------------------

    print(
        "Building lightweight data ZIP ..."
    )

    zip_staging_dir = (
        output_root_path
        / f"{release_name}-data"
    )

    if zip_staging_dir.exists():
        shutil.rmtree(
            zip_staging_dir
        )

    zip_staging_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    files_for_zip = [
        "README.md",
        "station_metadata.csv",
        "station_variable_year_audit.csv",
        "station_variable_year_audit.parquet",
        "hourly.parquet",
        "daily.parquet",
        "weekly.parquet",
        "monthly.parquet",
    ]

    for filename in files_for_zip:
        source_file = (
            release_dir / filename
        )

        if not source_file.exists():
            raise FileNotFoundError(
                f"Missing release file: "
                f"{source_file}"
            )

        shutil.copy2(
            source_file,
            zip_staging_dir / filename,
        )

    archive_base = (
        output_root_path
        / f"{release_name}-data"
    )

    zip_path = shutil.make_archive(
        str(archive_base),
        "zip",
        root_dir=output_root_path,
        base_dir=zip_staging_dir.name,
    )

    # Remove temporary ZIP staging folder.
    shutil.rmtree(
        zip_staging_dir
    )

    # -------------------------------------------------------------
    # Report outputs
    # -------------------------------------------------------------

    print()
    print(
        f"Release directory: "
        f"{release_dir}"
    )

    print(
        f"Data ZIP: "
        f"{zip_path}"
    )

    print(
        f"DuckDB: "
        f"{db_path}"
    )

    return Path(zip_path)