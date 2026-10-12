# Methodology

## Scope
This repository archives observed NOAA NCEI Global Historical Climatology Network-hourly (GHCNh) measurements. It does not forecast, interpolate, impute, or spatially model weather.

## Data layers
1. **Raw PSV**: exact station/year file downloaded from NOAA.
2. **Raw Parquet mirror**: all NOAA columns preserved for efficient inspection.
3. **Canonical observations**: a stable subset of research-facing fields plus provenance.
4. **Audit outputs**: station x year x variable record-presence metrics.

## Missingness
Missing values remain missing. Zero precipitation is not substituted for absent precipitation observations.

## WBGT
WBGT is not calculated. Wet-bulb temperature is retained if directly present in GHCNh. A future measured-WBGT source may be added as a distinct observational source.

## Time
Source DATE is parsed as UTC. Local time conversion is deferred to analysis so daylight-saving and Arizona time rules remain explicit and reproducible.

## Important precipitation note
GHCNh contains precipitation observations at multiple accumulation intervals. This v0.1 repository preserves those fields but does **not** yet publish a derived hourly/daily precipitation total. That will be added only after explicit accumulation/de-duplication rules are tested.
