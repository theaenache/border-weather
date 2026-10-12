from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


FIGURE_DIR = Path("reports/figures")
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_PATH = Path(
    "reports/audit/station_variable_year.csv"
)

HOURLY_PATH = Path(
    "releases/border-weather-v0.1/hourly.parquet"
)

STATION_LABELS = {
    "USW00012959": "McAllen",
    "USW00012919": "Brownsville",
    "USI0000KBRO": "Brownsville (parallel source)",
    "USW00012904": "Harlingen",
    "USW00012957": "Port Isabel",
    "USW00003145": "Yuma",
    "USW00023195": "Yuma (historical source)",
    "USI0000KLGF": "Laguna AAF",
    "USI0000KNOZ": "Yuma Aux / Wellton",
    "USW00003144": "Imperial",
    "USW00023199": "El Centro",
}

VARIABLE_LABELS = {
    "temperature": "Temperature",
    "dew_point_temperature": "Dew point",
    "relative_humidity": "Relative humidity",
    "wind_speed": "Wind speed",
    "wind_direction": "Wind direction",
    "wind_gust": "Wind gust",
    "station_level_pressure": "Station pressure",
    "sea_level_pressure": "Sea-level pressure",
    "visibility": "Visibility",
    "wet_bulb_temperature": "Wet-bulb temperature",
}


def coverage_over_time():
    audit = pd.read_csv(AUDIT_PATH)

    df = audit[
        audit["variable"] == "temperature"
    ].copy()

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    df = df[
        df["year"].between(2000, 2026)
    ]

    plt.figure(figsize=(10, 6))

    for station_id, group in df.groupby(
        "source_station_id"
    ):
        group = group.sort_values("year").copy()

        # Missing station-years should appear as gaps,
        # not as artificial zero coverage.
        group.loc[
            group["hours_with_observation"] == 0,
            "hourly_coverage_pct",
        ] = pd.NA

        label = STATION_LABELS.get(
            station_id,
            station_id,
        )

        plt.plot(
            group["year"],
            group["hourly_coverage_pct"],
            label=label,
        )

    plt.xlabel("Year")
    plt.ylabel("Hourly coverage (%)")
    plt.title("Temperature observation coverage")
    plt.ylim(0, 100)

    plt.legend(
        fontsize=8,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = (
        FIGURE_DIR
        / "temperature_coverage_by_station.png"
    )

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


def annual_temperature():
    df = pd.read_parquet(HOURLY_PATH)

    df["hour_utc"] = pd.to_datetime(
        df["hour_utc"],
        utc=True,
        errors="coerce",
    )

    df["year"] = df["hour_utc"].dt.year

    # Use complete years only.
    df = df[
        df["year"].between(2000, 2025)
    ].copy()

    df["temperature_mean"] = pd.to_numeric(
        df["temperature_mean"],
        errors="coerce",
    )

    df["temperature_n"] = pd.to_numeric(
        df["temperature_n"],
        errors="coerce",
    ).fillna(0)

    df = df[
        (df["temperature_n"] > 0)
        & df["temperature_mean"].notna()
    ].copy()

    # Weight hourly means by the number of
    # underlying temperature reports in that hour.
    df["weighted_temperature"] = (
        df["temperature_mean"]
        * df["temperature_n"]
    )

    annual = (
        df.groupby(
            [
                "source_station_id",
                "year",
            ],
            as_index=False,
        )
        .agg(
            weighted_sum=(
                "weighted_temperature",
                "sum",
            ),
            observation_count=(
                "temperature_n",
                "sum",
            ),
        )
    )

    annual["temperature_mean"] = (
        annual["weighted_sum"]
        / annual["observation_count"]
    )

    plt.figure(figsize=(10, 6))

    for station_id, group in annual.groupby(
        "source_station_id"
    ):
        group = group.sort_values("year")

        label = STATION_LABELS.get(
            station_id,
            station_id,
        )

        plt.plot(
            group["year"],
            group["temperature_mean"],
            label=label,
        )

    plt.xlabel("Year")
    plt.ylabel("Mean temperature (°C)")
    plt.title(
        "Annual mean observed temperature"
    )

    plt.legend(
        fontsize=8,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = (
        FIGURE_DIR
        / "annual_mean_temperature.png"
    )

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


def coverage_by_variable():
    audit = pd.read_csv(AUDIT_PATH)

    df = audit[
        audit["variable"].isin(
            VARIABLE_LABELS.keys()
        )
    ].copy()

    summary = (
        df.groupby(
            "variable",
            as_index=False,
        )["hourly_coverage_pct"]
        .mean()
    )

    summary["label"] = (
        summary["variable"]
        .map(VARIABLE_LABELS)
    )

    summary = summary.sort_values(
        "hourly_coverage_pct"
    )

    plt.figure(figsize=(8, 5.5))

    plt.barh(
        summary["label"],
        summary["hourly_coverage_pct"],
    )

    plt.xlabel("Mean hourly coverage (%)")
    plt.ylabel("")
    plt.title(
        "Average observation coverage by variable"
    )
    plt.xlim(0, 100)

    plt.tight_layout()

    path = (
        FIGURE_DIR
        / "coverage_by_variable.png"
    )

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


def build_all_figures():
    coverage_over_time()
    annual_temperature()
    coverage_by_variable()


if __name__ == "__main__":
    build_all_figures()