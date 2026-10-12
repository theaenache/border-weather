# Border Weather

Pipeline for collecting and summarizing **observed NOAA/NWS weather data** for selected U.S. border-county weather stations.

## Pipeline

- downloads historical and current observed weather data
- preserves NOAA source station IDs separately
- keeps missing observations as missing
- does not interpolate or model missing values
- creates hourly, daily, weekly, and monthly summary tables
- audits station and variable coverage over time
- builds shareable Parquet and DuckDB releases

## Variables

Summary tables currently include observed measures such as:

- temperature
- dew point
- relative humidity
- wind speed
- wind gust
- wind direction
- station pressure
- sea-level pressure
- visibility
- wet-bulb temperature, where available

Precipitation observations are preserved in the source data, but precipitation totals are not yet included in the summary tables because NOAA reports multiple overlapping accumulation periods.

## Data structure

Parallel NOAA source IDs are intentionally kept separate.

Use:

`site_key + source_station_id`

when grouping or comparing observations.

This avoids silently merging different NOAA reporting streams.

## Summary tables

The release includes:

- `hourly.parquet`
- `daily.parquet`
- `weekly.parquet`
- `monthly.parquet`

Parquet is used because it is compact, fast, and preserves timestamps and numeric data types well. These files can be opened directly in Python, R, DuckDB, and many other analysis tools.

## Data quality

`reports/audit/station_variable_year.csv`

contains station-variable-year completeness metrics, including:

- hourly coverage
- observed hours
- expected hours
- reporting frequency
- maximum observation gaps

## Releases

GitHub Releases contain ready-to-analyze data so yall do not need to run the ingestion pipeline yourself.

Recommended download:

`border-weather-v0.1-data.zip`

An optional DuckDB database is also provided for SQL-based analysis.

## Reproducibility

The repository contains the code used to:

1. ingest NOAA observations
2. build canonical station-level datasets
3. audit coverage
4. create temporal summaries
5. generate shareable research releases

Generated raw and processed datasets are not stored in normal Git history because of their size.

## Current scope

The current archive covers selected stations in:

- Hidalgo County, Texas
- Cameron County, Texas
- Yuma County, Arizona
- Imperial County, California

Historical coverage extends back to 2000 where available.
