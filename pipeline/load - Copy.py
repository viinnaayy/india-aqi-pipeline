"""LOAD: write cleaned rows into PostgreSQL (safe to re-run: no duplicates)."""
import os

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

COLUMNS = ["city_id", "reading_time", "pm2_5", "pm10", "no2", "so2", "co", "o3",
           "us_aqi", "temperature", "humidity", "wind_speed", "precipitation"]


def get_conn():
    load_dotenv()  # reads DATABASE_URL from the .env file
    return psycopg2.connect(os.environ["DATABASE_URL"])


def get_city_ids(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT city_name, city_id FROM dim_city")
        return dict(cur.fetchall())


def prepare_rows(df):
    """DataFrame -> list of tuples, with NaN turned into None (SQL NULL)."""
    sub = df[COLUMNS]
    sub = sub.astype(object).where(sub.notna(), None)
    rows = []
    for r in sub.itertuples(index=False, name=None):
        rows.append(tuple(v.to_pydatetime() if isinstance(v, pd.Timestamp) else v
                          for v in r))
    return rows


def upsert_readings(conn, df):
    """Insert new rows; if (city_id, reading_time) already exists, update it.

    This is what makes the pipeline IDEMPOTENT: running it twice gives the
    same result as running it once.
    """
    rows = prepare_rows(df)
    if not rows:
        return 0
    value_cols = COLUMNS[2:]
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in value_cols)
    sql = f"""
        INSERT INTO fact_readings ({", ".join(COLUMNS)}) VALUES %s
        ON CONFLICT (city_id, reading_time) DO UPDATE SET {updates}
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=5000)
    conn.commit()
    return len(rows)


def log_run(conn, city, rows_loaded, status, error=None):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pipeline_runs (city_name, rows_loaded, status, error) "
            "VALUES (%s, %s, %s, %s)",
            (city, rows_loaded, status, error),
        )
    conn.commit()
