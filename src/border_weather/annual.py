from pathlib import Path

import pandas as pd


DAILY_PATH = Path(
    "releases/border-weather-v0.1/daily.parquet"
)

OUTPUT_PATH = Path(
    "data/processed/summaries/annual/annual.parquet"
)


def build_annual_summary():
    df = pd.read_parquet(DAILY_PATH)

    df["local_date"] = pd.to_datetime(
        df["local_date"],
        errors="coerce",
    )

    df["year"] = df["local_date"].dt.year

    df["temperature_mean"] = pd.to_numeric(
        df["temperature_mean"],
        errors="coerce",
    )

    df["temperature_hours"] = pd.to_numeric(
        df["temperature_hours"],
        errors="coerce",
    ).fillna(0)

    temp = df[
        (df["temperature_hours"] > 0)
        & df["temperature_mean"].notna()
    ].copy()

    temp["temperature_weighted"] = (
        temp["temperature_mean"]
        * temp["temperature_hours"]
    )

    group_cols = [
        "site_key",
        "source_station_id",
        "county",
        "county_fips",
        "state",
        "timezone",
        "identifier_role",
        "year",
    ]

    annual = (
        temp.groupby(
            group_cols,
            as_index=False,
        )
        .agg(
            temperature_weighted_sum=(
                "temperature_weighted",
                "sum",
            ),
            temperature_hours=(
                "temperature_hours",
                "sum",
            ),
            days_with_temperature=(
                "local_date",
                "nunique",
            ),
        )
    )

    annual["annual_mean_temperature"] = (
        annual["temperature_weighted_sum"]
        / annual["temperature_hours"]
    )

    annual = annual.drop(
        columns=["temperature_weighted_sum"]
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    annual.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print(
        f"Wrote {len(annual):,} annual rows to "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    build_annual_summary()