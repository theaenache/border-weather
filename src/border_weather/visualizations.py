from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

FIGURE_DIR = Path("reports/figures")
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_PATH = Path(
    "reports/audit/station_variable_year.csv"
)

DAILY_PATH = Path(
    "releases/border-weather-v0.1/daily.parquet"
)

MONTHLY_PATH = Path(
    "releases/border-weather-v0.1/monthly.parquet"
)

ANNUAL_PATH = Path(
    "data/processed/summaries/annual/annual.parquet"
)


# ---------------------------------------------------------
# Labels
# ---------------------------------------------------------

STATION_LABELS = {
    "USW00012959": "McAllen Miller Intl Airport",
    "USW00012919": "Brownsville/South Padre Island Intl Airport",
    "USI0000KBRO": (
        "Brownsville/South Padre Island Intl Airport "
        "(parallel source)"
    ),
    "USW00012904": "Valley Intl Airport (Harlingen)",
    "USW00012957": "Port Isabel–Cameron County Airport",
    "USW00003145": "Yuma Intl Airport",
    "USW00023195": "Yuma Airport (historical source)",
    "USI0000KLGF": "Laguna Army Airfield",
    "USI0000KNOZ": "Yuma Auxiliary Airfield / Wellton",
    "USW00003144": "Imperial County Airport",
    "USW00023199": "El Centro Naval Air Facility",
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


def _station_label(station_id):
    return STATION_LABELS.get(
        station_id,
        station_id,
    )


# ---------------------------------------------------------
# 1. Annual mean temperature
# ---------------------------------------------------------

def annual_temperature():
    df = pd.read_parquet(ANNUAL_PATH)

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    df["annual_mean_temperature"] = pd.to_numeric(
        df["annual_mean_temperature"],
        errors="coerce",
    )

    df = df[
        df["year"].notna()
        & df["annual_mean_temperature"].notna()
    ].copy()

    plt.figure(figsize=(11, 6))

    for station_id, group in df.groupby(
        "source_station_id"
    ):
        group = group.sort_values("year")

        plt.plot(
            group["year"],
            group["annual_mean_temperature"],
            label=_station_label(station_id),
        )

    plt.xlabel("Year")
    plt.ylabel("Mean temperature (°C)")
    plt.title("Annual mean observed temperature")

    plt.legend(
        fontsize=7.5,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = FIGURE_DIR / "annual_mean_temperature.png"

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


# ---------------------------------------------------------
# 2. Average coverage by variable
# ---------------------------------------------------------

def coverage_by_variable():
    audit = pd.read_csv(AUDIT_PATH)

    df = audit[
        audit["variable"].isin(
            VARIABLE_LABELS.keys()
        )
    ].copy()

    df["hourly_coverage_pct"] = pd.to_numeric(
        df["hourly_coverage_pct"],
        errors="coerce",
    )

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
    plt.title("Average observation coverage by variable")
    plt.xlim(0, 100)

    plt.tight_layout()

    path = FIGURE_DIR / "coverage_by_variable.png"

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


# ---------------------------------------------------------
# 3. Station-year coverage heatmap
# ---------------------------------------------------------

def coverage_heatmap():
    audit = pd.read_csv(AUDIT_PATH)

    df = audit[
        audit["variable"] == "temperature"
    ].copy()

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    df["hourly_coverage_pct"] = pd.to_numeric(
        df["hourly_coverage_pct"],
        errors="coerce",
    )

    df["station_label"] = (
        df["source_station_id"]
        .map(STATION_LABELS)
        .fillna(df["source_station_id"])
    )

    pivot = df.pivot_table(
        index="station_label",
        columns="year",
        values="hourly_coverage_pct",
        aggfunc="mean",
    )

    plt.figure(figsize=(12, 6))

    image = plt.imshow(
        pivot,
        aspect="auto",
        interpolation="nearest",
        vmin=0,
        vmax=100,
    )

    plt.yticks(
        range(len(pivot.index)),
        pivot.index,
        fontsize=8,
    )

    years = list(pivot.columns)

    step = 2
    tick_positions = list(
        range(0, len(years), step)
    )

    plt.xticks(
        tick_positions,
        [
            int(years[i])
            for i in tick_positions
        ],
        rotation=45,
        ha="right",
    )

    plt.xlabel("Year")
    plt.ylabel("")
    plt.title("Temperature observation coverage by station and year")

    colorbar = plt.colorbar(image)
    colorbar.set_label("Hourly coverage (%)")

    plt.tight_layout()

    path = FIGURE_DIR / "temperature_coverage_heatmap.png"

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


# ---------------------------------------------------------
# 4. Seasonal temperature profile
# ---------------------------------------------------------

def seasonal_temperature_profile():
    df = pd.read_parquet(MONTHLY_PATH)

    df["month_start_local"] = pd.to_datetime(
        df["month_start_local"],
        errors="coerce",
    )

    df["temperature_mean"] = pd.to_numeric(
        df["temperature_mean"],
        errors="coerce",
    )

    df = df[
        df["month_start_local"].notna()
        & df["temperature_mean"].notna()
    ].copy()

    df["month"] = (
        df["month_start_local"].dt.month
    )

    seasonal = (
        df.groupby(
            [
                "source_station_id",
                "month",
            ],
            as_index=False,
        )["temperature_mean"]
        .mean()
    )

    plt.figure(figsize=(10, 6))

    for station_id, group in seasonal.groupby(
        "source_station_id"
    ):
        group = group.sort_values("month")

        plt.plot(
            group["month"],
            group["temperature_mean"],
            label=_station_label(station_id),
        )

    plt.xticks(
        range(1, 13),
        [
            "Jan", "Feb", "Mar", "Apr",
            "May", "Jun", "Jul", "Aug",
            "Sep", "Oct", "Nov", "Dec",
        ],
    )

    plt.xlabel("Month")
    plt.ylabel("Mean temperature (°C)")
    plt.title("Seasonal temperature profile")

    plt.legend(
        fontsize=7.5,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = FIGURE_DIR / "seasonal_temperature_profile.png"

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


# ---------------------------------------------------------
# 5. Annual temperature anomaly
# ---------------------------------------------------------

def annual_temperature_anomaly():
    df = pd.read_parquet(ANNUAL_PATH)

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    df["annual_mean_temperature"] = pd.to_numeric(
        df["annual_mean_temperature"],
        errors="coerce",
    )

    df = df[
        df["year"].notna()
        & df["annual_mean_temperature"].notna()
    ].copy()

    long_term_mean = (
        df.groupby("source_station_id")[
            "annual_mean_temperature"
        ]
        .transform("mean")
    )

    df["temperature_anomaly"] = (
        df["annual_mean_temperature"]
        - long_term_mean
    )

    plt.figure(figsize=(11, 6))

    for station_id, group in df.groupby(
        "source_station_id"
    ):
        group = group.sort_values("year")

        plt.plot(
            group["year"],
            group["temperature_anomaly"],
            label=_station_label(station_id),
        )

    plt.axhline(
        0,
        linewidth=1,
    )

    plt.xlabel("Year")
    plt.ylabel("Temperature anomaly (°C)")
    plt.title(
        "Annual temperature relative to each station's observed mean"
    )

    plt.legend(
        fontsize=7.5,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = FIGURE_DIR / "annual_temperature_anomaly.png"

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


# ---------------------------------------------------------
# 6. Extreme heat days
# ---------------------------------------------------------

def extreme_heat_days(
    threshold_c=35.0,
):
    df = pd.read_parquet(DAILY_PATH)

    df["local_date"] = pd.to_datetime(
        df["local_date"],
        errors="coerce",
    )

    df["temperature_max"] = pd.to_numeric(
        df["temperature_max"],
        errors="coerce",
    )

    df = df[
        df["local_date"].notna()
        & df["temperature_max"].notna()
    ].copy()

    df["year"] = (
        df["local_date"].dt.year
    )

    df["extreme_heat_day"] = (
        df["temperature_max"] >= threshold_c
    )

    annual = (
        df.groupby(
            [
                "source_station_id",
                "year",
            ],
            as_index=False,
        )["extreme_heat_day"]
        .sum()
    )

    plt.figure(figsize=(11, 6))

    for station_id, group in annual.groupby(
        "source_station_id"
    ):
        group = group.sort_values("year")

        plt.plot(
            group["year"],
            group["extreme_heat_day"],
            label=_station_label(station_id),
        )

    plt.xlabel("Year")
    plt.ylabel(
        f"Days with max temperature ≥ {threshold_c:.0f}°C"
    )

    plt.title(
        f"Extreme heat days per year (≥ {threshold_c:.0f}°C)"
    )

    plt.legend(
        fontsize=7.5,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = FIGURE_DIR / "extreme_heat_days_per_year.png"

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


# ---------------------------------------------------------
# Build all figures
# ---------------------------------------------------------

def build_all_figures():
    annual_temperature()
    coverage_by_variable()
    coverage_heatmap()
    seasonal_temperature_profile()
    annual_temperature_anomaly()
    extreme_heat_days()


if __name__ == "__main__":
    build_all_figures()