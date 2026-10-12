# Border Weather Observations

A reproducible archive of **observed** NOAA NCEI GHCNh weather measurements for nine initial surface stations in Hidalgo County TX, Cameron County TX, Yuma County AZ, and Imperial County CA.

## Scope

- No forecasts, interpolation, imputation, or modeled WBGT.
- **2000-present**. (alvaro lmk if you want this changed)
- Daily automated current year refresh.
- Raw NOAA rows and provenance are preserved.
- Canonical Parquet output is queryable with Python, R, DuckDB, or other Arrow compatible tools.

## Initial sites

| Site key | County | Station |
|---|---|---|
| `mcallen` | Hidalgo, TX | McAllen Miller International Airport |
| `brownsville` | Cameron, TX | Brownsville/South Padre Island International Airport |
| `harlingen` | Cameron, TX | Valley International Airport |
| `port_isabel` | Cameron, TX | Port Isabel-Cameron County Airport |
| `yuma` | Yuma, AZ | Yuma International / MCAS |
| `laguna` | Yuma, AZ | Laguna Army Airfield |
| `yuma_aux` | Yuma, AZ | Yuma Auxiliary / Wellton |
| `imperial` | Imperial, CA | Imperial County Airport |
| `el_centro` | Imperial, CA | El Centro Naval Air Facility |

See `config/stations.yml` for GHCNh identifiers. Brownsville and Yuma historical/current identifier relationships are deliberately marked for final live-inventory verification before a publication-quality release.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Historical backfill

```bash
border-weather backfill --start 2000
```

A single-site test run:

```bash
border-weather backfill --start 2025 --end 2025 --station mcallen
```

## Daily update

```bash
border-weather update
border-weather audit
border-weather build-db
```

GitHub Actions runs the same sequence daily at 11:23 UTC and can also be triggered manually from the Actions tab. Times will be recorded in UTC due to varying time zones. 

## Query

```python
import duckdb

con = duckdb.connect("data/border_weather.duckdb")
df = con.sql("""
    SELECT site_key, timestamp_utc, temperature, wind_speed, wind_direction
    FROM observations
    WHERE site_key = 'mcallen'
      AND timestamp_utc >= '2025-01-01'
    ORDER BY timestamp_utc
""").df()
```

## Doing a quick station audit rn! Format:

```bash
border-weather audit
```

Produces:

- `reports/audit/station_variable_year.parquet`
- `reports/audit/station_variable_year.csv`

The initial audit reports **record presence**, not yet true expected-hour completeness. GHCNh may contain multiple reports per hour; expected-hour coverage will be implemented after report-type selection rules are established from the backfilled records. Work in progress!


Station/year files follow this pattern:

```text
https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/access/by-year/<YEAR>/psv/GHCNh_<STATION>_<YEAR>.psv
```

## License

Code: MIT. NOAA data remain subject to NOAA/NCEI terms and attribution practices.
