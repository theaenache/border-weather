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

WEEKLY_PATH = Path(
    "releases/border-weather-v0.1/weekly.parquet"
)

MONTHLY_PATH = Path(
    "releases/border-weather-v0.1/monthly.parquet"
)

ANNUAL_PATH = Path(
    "data/processed/summaries/annual/annual.parquet"
)


# ---------------------------------------------------------
# Human-readable labels
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


# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------

def _station_label(station_id):
    return STATION_LABELS.get(
        station_id,
        station_id,
    )


# ---------------------------------------------------------
# 1. Temperature coverage over time
# ---------------------------------------------------------

def coverage_over_time():
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

    df["hours_with_observation"] = pd.to_numeric(
        df["hours_with_observation"],
        errors="coerce",
    )

    plt.figure(figsize=(11, 6))

    for station_id, group in df.groupby(
        "source_station_id"
    ):
        group = group.sort_values("year").copy()

        # No observations = gap, not zero coverage.
        group.loc[
            group["hours_with_observation"] == 0,
            "hourly_coverage_pct",
        ] = pd.NA

        plt.plot(
            group["year"],
            group["hourly_coverage_pct"],
            label=_station_label(station_id),
        )

    plt.xlabel("Year")
    plt.ylabel("Hourly coverage (%)")
    plt.title(
        "Temperature observation coverage by station"
    )
    plt.ylim(0, 100)

    plt.legend(
        fontsize=7.5,
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


# ---------------------------------------------------------
# 2. Coverage by variable
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


# ---------------------------------------------------------
# 3. Weekly temperature
# ---------------------------------------------------------

def weekly_temperature():
    df = pd.read_parquet(WEEKLY_PATH)

    df["week_start_local"] = pd.to_datetime(
        df["week_start_local"],
        errors="coerce",
    )

    df["temperature_mean"] = pd.to_numeric(
        df["temperature_mean"],
        errors="coerce",
    )

    df = df[
        df["week_start_local"].notna()
        & df["temperature_mean"].notna()
    ].copy()

    plt.figure(figsize=(12, 6))

    for station_id, group in df.groupby(
        "source_station_id"
    ):
        group = group.sort_values(
            "week_start_local"
        )

        plt.plot(
            group["week_start_local"],
            group["temperature_mean"],
            label=_station_label(station_id),
            linewidth=0.9,
        )

    plt.xlabel("Week")
    plt.ylabel("Mean temperature (°C)")
    plt.title(
        "Weekly mean observed temperature"
    )

    plt.legend(
        fontsize=7,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = (
        FIGURE_DIR
        / "weekly_mean_temperature.png"
    )

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


# ---------------------------------------------------------
# 4. Monthly temperature
# ---------------------------------------------------------

def monthly_temperature():
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

    plt.figure(figsize=(12, 6))

    for station_id, group in df.groupby(
        "source_station_id"
    ):
        group = group.sort_values(
            "month_start_local"
        )

        plt.plot(
            group["month_start_local"],
            group["temperature_mean"],
            label=_station_label(station_id),
            linewidth=1.1,
        )

    plt.xlabel("Month")
    plt.ylabel("Mean temperature (°C)")
    plt.title(
        "Monthly mean observed temperature"
    )

    plt.legend(
        fontsize=7,
        ncol=2,
        frameon=False,
    )

    plt.tight_layout()

    path = (
        FIGURE_DIR
        / "monthly_mean_temperature.png"
    )

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(path)


# ---------------------------------------------------------
# 5. Annual temperature
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
    plt.title(
        "Annual mean observed temperature"
    )

    plt.legend(
        fontsize=7.5,
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


# ---------------------------------------------------------
# Build everything
# ---------------------------------------------------------

def build_all_figures():
    coverage_over_time()
    coverage_by_variable()
    weekly_temperature()
    monthly_temperature()
    annual_temperature()


if __name__ == "__main__":
    build_all_figures()