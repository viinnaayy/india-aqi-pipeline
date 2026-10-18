"""Run ONCE: create the tables and fill the city table.

    python -m pipeline.setup_db
"""
from pathlib import Path

from .config import CITIES
from .load import get_conn


def main():
    schema_path = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute(schema_path.read_text())
        for name, state, region, lat, lon in CITIES:
            cur.execute(
                """INSERT INTO dim_city (city_name, state, region, latitude, longitude)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (city_name) DO UPDATE
                   SET state = EXCLUDED.state, region = EXCLUDED.region,
                       latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude""",
                (name, state, region, lat, lon),
            )
    conn.close()
    print(f"Database ready. {len(CITIES)} cities loaded.")


if __name__ == "__main__":
    main()
