from __future__ import annotations
from pathlib import Path


def build_duckdb(db_path: str = "data/border_weather.duckdb") -> None:
    import duckdb
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(db_path)
    try:
        con.execute("DROP VIEW IF EXISTS observations")
        con.execute("""
            CREATE VIEW observations AS
            SELECT * FROM read_parquet(
              'data/processed/observations/year=*/site_key=*/source_station_id=*/observations.parquet',
              hive_partitioning = true,
              union_by_name = true
            )
        """)
    finally:
        con.close()
