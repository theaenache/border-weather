from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


FIGURE_DIR = Path("reports/figures")
FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def coverage_over_time():
    audit = pd.read_csv(
        "reports/audit/station_variable_year.csv"
    )

    df = audit[
        audit["variable"] == "temperature"
    ].copy()

    plt.figure(figsize=(10, 6))

    for station_id, group in df.groupby(
        "source_station_id"
    ):
        group = group.sort_values("year")

        plt.plot(
            group["year"],
            group["hourly_coverage_pct"],
            label=station_id,
        )

    plt.xlabel("Year")
    plt.ylabel("Hourly coverage (%)")
    plt.title("Temperature observation coverage by station")
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
    df = pd.read_parquet(
        "releases/border-weather-v0.1/"
        "monthly.parquet"
    )

    df["month_start_local"] = pd.to_datetime(
        df["month_start_local"]
    )

    df["year"] = (
        df["month_start_local"].dt.year
    )

    annual = (
        df.groupby(
            [
                "source_station_id",
                "year",
            ],
            as_index=False,
        )["temperature_mean"]
        .mean()
    )

    plt.figure(figsize=(10, 6))

    for station_id, group in annual.groupby(
        "source_station_id"
    ):
        group = group.sort_values("year")

        plt.plot(
            group["year"],
            group["temperature_mean"],
            label=station_id,
        )

    plt.xlabel("Year")
    plt.ylabel("Mean temperature (°C)")
    plt.title("Annual mean temperature by station")

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
    audit = pd.read_csv(
        "reports/audit/station_variable_year.csv"
    )

    summary = (
        audit.groupby(
            "variable",
            as_index=False,
        )["hourly_coverage_pct"]
        .mean()
        .sort_values(
            "hourly_coverage_pct"
        )
    )

    plt.figure(figsize=(8, 6))

    plt.barh(
        summary["variable"],
        summary["hourly_coverage_pct"],
    )

    plt.xlabel("Mean hourly coverage (%)")
    plt.ylabel("")
    plt.title("Average data coverage by variable")
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