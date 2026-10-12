from __future__ import annotations
from datetime import datetime, timezone
import typer
from .pipeline import backfill as run_backfill, update_current_year
from .audit import build_audit
from .db import build_duckdb

app = typer.Typer(help="Observed NOAA GHCNh weather archive pipeline.")

@app.command()
def backfill(start: int = 2000, end: int | None = None, station: list[str] | None = typer.Option(None)):
    """Download and ingest station/year observations."""
    end = end or datetime.now(timezone.utc).year
    df = run_backfill(start, end, set(station or []) or None)
    typer.echo(df["status"].value_counts(dropna=False).to_string())

@app.command()
def update():
    """Refresh every configured station identifier for the current calendar year."""
    df = update_current_year()
    typer.echo(df["status"].value_counts(dropna=False).to_string())

@app.command("audit")
def audit_cmd():
    """Build station x year x variable availability audit."""
    df = build_audit()
    typer.echo(f"Wrote {len(df):,} audit rows")

@app.command("build-db")
def build_db_cmd():
    """Create a DuckDB view over the canonical Parquet archive."""
    build_duckdb()
    typer.echo("Built data/border_weather.duckdb")

if __name__ == "__main__":
    app()
