"""Run the pipeline: fetch -> clean -> load, for every city.

Examples (run from the project folder):
    python -m pipeline.run --city Delhi --start 2024-01-01 --end 2024-01-07   # tiny test
    python -m pipeline.run                                                    # full history
    python -m pipeline.run --only-missing                                     # finish a half-done load
    python -m pipeline.run --days 3                                           # daily refresh
"""
import argparse
import sys
import time
from datetime import date, timedelta

from .clean import clean
from .config import CITIES, START_DATE
from .fetch import fetch_city
from .load import get_city_ids, get_conn, loaded_counts, log_run, upsert_readings


def main():
    parser = argparse.ArgumentParser(description="India AQI pipeline")
    parser.add_argument("--start", default=START_DATE, help="YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--days", type=int, default=None,
                        help="only load the last N days (for daily refresh)")
    parser.add_argument("--city", default=None, help="only this city (for testing)")
    parser.add_argument("--only-missing", action="store_true",
                        help="skip cities that already have (almost) all their data")
    args = parser.parse_args()

    yesterday = date.today() - timedelta(days=1)
    end = args.end or yesterday.isoformat()
    start = (date.today() - timedelta(days=args.days)).isoformat() if args.days else args.start

    conn = get_conn()
    city_ids = get_city_ids(conn)

    counts = {}
    expected = 0
    if args.only_missing:
        expected = ((date.fromisoformat(end) - date.fromisoformat(start)).days + 1) * 24
        counts = loaded_counts(conn)

    ok = failed = skipped = 0

    for name, state, region, lat, lon in CITIES:
        if args.city and name.lower() != args.city.lower():
            continue
        if args.only_missing and counts.get(city_ids[name], 0) >= 0.9 * expected:
            print(f"[SKIP] {name}: already loaded")
            skipped += 1
            continue
        try:
            df = fetch_city(lat, lon, start, end)
            df["city_id"] = city_ids[name]
            df = clean(df)
            n = upsert_readings(conn, df)
            log_run(conn, name, n, "success")
            ok += 1
            print(f"[OK]   {name}: {n} rows ({start} to {end})", flush=True)
        except Exception as e:  # keep going so one bad city doesn't stop the rest
            conn.rollback()
            log_run(conn, name, 0, "failed", str(e)[:500])
            failed += 1
            print(f"[FAIL] {name}: {e}", flush=True)
        time.sleep(3)  # be polite to the free API

    conn.close()
    print(f"\nDone: {ok} loaded, {skipped} skipped, {failed} failed.")
    sys.exit(1 if failed else 0)  # non-zero exit makes GitHub Actions show a red cross


if __name__ == "__main__":
    main()
