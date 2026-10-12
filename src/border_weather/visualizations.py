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


MONTH_LABELS = [
    "Jan", "Feb", "Mar", "Apr",
    "May", "Jun", "Jul", "Aug",
    "Sep", "Oct", "Nov", "Dec",
]


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
# 3. Seasonal extreme heat
# ---------------------------------------------------------

def seasonal_extreme_heat(
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

    df["month"] = df["local_date"].dt.month
    df["year"] = df["local_date"].dt.year

    df["extreme_heat_day"] = (
        df["temperature_max"] >= threshold_c
    )

    yearly_monthly = (
        df.groupby(
            [
                "source_station_id",
                "year",
                "month",
            ],
            as_index=False,
        )["extreme_heat_day"]
        .sum()
    )

    seasonal = (
        yearly_monthly.groupby(
            [
                "source_station_id",
                "month",
            ],
            as_index=False,
        )["extreme_heat_day"]
        .mean()
    )

    plt.figure(figsize=(10, 6))

    for station_id, group in seasonal.groupby(
        "source_station_id"
    ):
        group = group.sort_values("month")

        plt.plot(
            group["month"],
            group["extreme_heat_day"],
            label=_station_label(station_id),
        )

    plt.xticks(
        range(1, 13),
        MONTH_LABELS,
    )

    plt.xlabel("Month")
    plt.ylabel(
        f"Mean days per month ≥ {threshold_c:.0f}°C"
    )
    plt.title(
        f"Seasonal extreme heat frequency (≥ {threshold_c:.0f}°C)"
    )

    plt.legend(
        fontsize=7.5,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = (
        FIGURE_DIR
        / "seasonal_extreme_heat.png"
    )

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


# ---------------------------------------------------------
# 4. Relative humidity seasonal profile
# ---------------------------------------------------------

def seasonal_relative_humidity():
    df = pd.read_parquet(MONTHLY_PATH)

    df["month_start_local"] = pd.to_datetime(
        df["month_start_local"],
        errors="coerce",
    )

    df["relative_humidity_mean"] = pd.to_numeric(
        df["relative_humidity_mean"],
        errors="coerce",
    )

    df = df[
        df["month_start_local"].notna()
        & df["relative_humidity_mean"].notna()
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
        )["relative_humidity_mean"]
        .mean()
    )

    plt.figure(figsize=(10, 6))

    for station_id, group in seasonal.groupby(
        "source_station_id"
    ):
        group = group.sort_values("month")

        plt.plot(
            group["month"],
            group["relative_humidity_mean"],
            label=_station_label(station_id),
        )

    plt.xticks(
        range(1, 13),
        MONTH_LABELS,
    )

    plt.xlabel("Month")
    plt.ylabel("Mean relative humidity (%)")
    plt.title("Seasonal relative humidity profile")

    plt.legend(
        fontsize=7.5,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = (
        FIGURE_DIR
        / "seasonal_relative_humidity.png"
    )

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


# ---------------------------------------------------------
# 5. Wet-bulb seasonal profile
# ---------------------------------------------------------

def seasonal_wet_bulb():
    df = pd.read_parquet(MONTHLY_PATH)

    df["month_start_local"] = pd.to_datetime(
        df["month_start_local"],
        errors="coerce",
    )

    df["wet_bulb_temperature_mean"] = pd.to_numeric(
        df["wet_bulb_temperature_mean"],
        errors="coerce",
    )

    df = df[
        df["month_start_local"].notna()
        & df["wet_bulb_temperature_mean"].notna()
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
        )["wet_bulb_temperature_mean"]
        .mean()
    )

    plt.figure(figsize=(10, 6))

    for station_id, group in seasonal.groupby(
        "source_station_id"
    ):
        group = group.sort_values("month")

        plt.plot(
            group["month"],
            group["wet_bulb_temperature_mean"],
            label=_station_label(station_id),
        )

    plt.xticks(
        range(1, 13),
        MONTH_LABELS,
    )

    plt.xlabel("Month")
    plt.ylabel("Mean wet-bulb temperature (°C)")
    plt.title("Seasonal observed wet-bulb temperature")

    plt.legend(
        fontsize=7.5,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = (
        FIGURE_DIR
        / "seasonal_wet_bulb_temperature.png"
    )

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


# ---------------------------------------------------------
# 6. Temperature vs humidity scatterplots
# ---------------------------------------------------------

def temperature_vs_humidity():
    df = pd.read_parquet(DAILY_PATH)

    df["temperature_mean"] = pd.to_numeric(
        df["temperature_mean"],
        errors="coerce",
    )

    df["relative_humidity_mean"] = pd.to_numeric(
        df["relative_humidity_mean"],
        errors="coerce",
    )

    df = df[
        df["temperature_mean"].notna()
        & df["relative_humidity_mean"].notna()
    ].copy()

    for station_id, group in df.groupby(
        "source_station_id"
    ):
        plt.figure(figsize=(7, 5.5))

        plt.scatter(
            group["temperature_mean"],
            group["relative_humidity_mean"],
            s=8,
            alpha=0.25,
        )

        plt.xlabel("Daily mean temperature (°C)")
        plt.ylabel("Daily mean relative humidity (%)")

        plt.title(
            "Temperature vs relative humidity\n"
            f"{_station_label(station_id)}"
        )

        plt.tight_layout()

        safe_station_id = (
            station_id
            .replace("/", "_")
            .replace("\\", "_")
        )

        path = (
            FIGURE_DIR
            / (
                "temperature_vs_humidity_"
                f"{safe_station_id}.png"
            )
        )

        plt.savefig(
            path,
            dpi=200,
            bbox_inches="tight",
        )

        plt.close()

        print(path)


# ---------------------------------------------------------
# 7. Warm nights
# ---------------------------------------------------------

def warm_nights(
    threshold_c=25.0,
):
    df = pd.read_parquet(DAILY_PATH)

    df["local_date"] = pd.to_datetime(
        df["local_date"],
        errors="coerce",
    )

    df["temperature_min"] = pd.to_numeric(
        df["temperature_min"],
        errors="coerce",
    )

    df = df[
        df["local_date"].notna()
        & df["temperature_min"].notna()
    ].copy()

    df["year"] = (
        df["local_date"].dt.year
    )

    df["warm_night"] = (
        df["temperature_min"] >= threshold_c
    )

    annual = (
        df.groupby(
            [
                "source_station_id",
                "year",
            ],
            as_index=False,
        )["warm_night"]
        .sum()
    )

    plt.figure(figsize=(11, 6))

    for station_id, group in annual.groupby(
        "source_station_id"
    ):
        group = group.sort_values("year")

        plt.plot(
            group["year"],
            group["warm_night"],
            label=_station_label(station_id),
        )

    plt.xlabel("Year")
    plt.ylabel(
        f"Days with minimum temperature ≥ {threshold_c:.0f}°C"
    )

    plt.title(
        f"Warm nights per year (minimum ≥ {threshold_c:.0f}°C)"
    )

    plt.legend(
        fontsize=7.5,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = (
        FIGURE_DIR
        / "warm_nights_per_year.png"
    )

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


# ---------------------------------------------------------
# 8. Day-to-night temperature range
# ---------------------------------------------------------

def day_night_temperature_range():
    df = pd.read_parquet(DAILY_PATH)

    df["local_date"] = pd.to_datetime(
        df["local_date"],
        errors="coerce",
    )

    df["temperature_max"] = pd.to_numeric(
        df["temperature_max"],
        errors="coerce",
    )

    df["temperature_min"] = pd.to_numeric(
        df["temperature_min"],
        errors="coerce",
    )

    df = df[
        df["local_date"].notna()
        & df["temperature_max"].notna()
        & df["temperature_min"].notna()
    ].copy()

    df["month"] = (
        df["local_date"].dt.month
    )

    df["temperature_range"] = (
        df["temperature_max"]
        - df["temperature_min"]
    )

    seasonal = (
        df.groupby(
            [
                "source_station_id",
                "month",
            ],
            as_index=False,
        )["temperature_range"]
        .mean()
    )

    plt.figure(figsize=(10, 6))

    for station_id, group in seasonal.groupby(
        "source_station_id"
    ):
        group = group.sort_values("month")

        plt.plot(
            group["month"],
            group["temperature_range"],
            label=_station_label(station_id),
        )

    plt.xticks(
        range(1, 13),
        MONTH_LABELS,
    )

    plt.xlabel("Month")
    plt.ylabel(
        "Mean daily temperature range (°C)"
    )

    plt.title(
        "Seasonal day-to-night temperature range"
    )

    plt.legend(
        fontsize=7.5,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = (
        FIGURE_DIR
        / "seasonal_day_night_temperature_range.png"
    )

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
    seasonal_extreme_heat()
    seasonal_relative_humidity()
    seasonal_wet_bulb()
    temperature_vs_humidity()
    warm_nights()
    day_night_temperature_range()


if __name__ == "__main__":
    build_all_figures()