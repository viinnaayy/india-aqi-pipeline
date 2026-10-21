# India Air Quality Data Pipeline & Dashboard

An automated pipeline that collects hourly air quality and weather data for 20 Indian cities, stores it in a PostgreSQL star schema, analyses it with SQL, refreshes itself every day, and shows the results in a live dashboard.

**Live dashboard:** YOUR_DASHBOARD_LINK

> The free hosting puts the app to sleep when nobody is using it. If you see a "wake this app up" button, click it and wait about 30 seconds.

## Problem statement

India has some of the most polluted cities in the world, but air quality data is scattered across sources, changes daily, and is hard to interpret. Most analyses are one-time snapshots that go out of date quickly.

This project builds an automated pipeline and dashboard that answer:

1. Which cities have the worst air quality, and how has it changed over time?
2. Which months and seasons are the most polluted?
3. How do temperature, wind, humidity and rain relate to pollution?
4. How often does each city exceed the safe PM2.5 limits (India NAAQS and WHO)?
5. Which days were extreme, and what were the conditions?

## Key findings

Period: January 2023 to October 2026, 20 cities, about 660,000 hourly records. Limits used: PM2.5 24-hour limit of 60 ug/m3 (India NAAQS) and 15 ug/m3 (WHO 2021); annual standards of 40 ug/m3 (India) and 5 ug/m3 (WHO 2021).

| City | Average PM2.5 (ug/m3) | % of days above India 24-hour limit | Longest unsafe streak (days) |
|---|---|---|---|
| Delhi | 73.2 | 55.6 | 45 |
| Ludhiana | 65.1 | 42.7 | 74 |
| Patna | 59.2 | 38.3 | 88 |
| Lucknow | 56.2 | 33.0 | 67 |
| Kolkata | 55.7 | 36.7 | 111 |
| Kanpur | 54.8 | 32.3 | 57 |
| Kochi | 24.3 | 0.7 | 2 |
| Chennai | 22.2 | 0.3 | 2 |
| Bengaluru | 20.9 | 0.1 | 1 |

- **Delhi is the most polluted city.** Its average PM2.5 is 73.2 ug/m3, about 1.8 times India's annual standard (40) and about 14.6 times the WHO annual guideline (5). It exceeded India's 24-hour limit on 55.6% of days and the WHO 24-hour guideline on every day.
- **Eight of 20 cities average above India's annual standard of 40 ug/m3:** Delhi, Ludhiana, Patna, Lucknow, Kolkata, Kanpur, Chandigarh and Bhubaneswar.
- **No city meets the WHO annual guideline.** Even the cleanest city, Bengaluru (20.9 ug/m3), is about 4.2 times the guideline.
- **A clear break separates six cities from the rest.** Delhi, Ludhiana, Patna, Lucknow, Kolkata and Kanpur rank highest both by average PM2.5 and by share of unsafe days.
- **Kolkata had the longest unsafe streak: 111 consecutive days** above the India 24-hour limit (9 November 2025 to 27 February 2026). Five of the six worst cities had their longest streak in winter 2025-26.
- **Nine of 20 cities exceeded the WHO 24-hour guideline on more than 90% of days**, which shows how much stricter the WHO benchmark is than India's standard.
- **The four cities with the fewest unsafe days are all in South India:** Bengaluru, Chennai, Kochi and Hyderabad.
- Seasonal patterns by city can be explored in the dashboard's season heatmap.

## Architecture

```
Open-Meteo APIs (air quality + weather)
        |
        v
Python: fetch -> clean -> load (retries, validation, upserts)
        |
        v
PostgreSQL (Neon): star schema + daily summary view
        |                         |
        v                         v
SQL analysis            Streamlit dashboard (public link)

GitHub Actions: runs the pipeline every morning (08:00 IST)
```

## Tech stack

Python (pandas, requests, psycopg2), PostgreSQL, SQL (CTEs, window functions), Git and GitHub, GitHub Actions, Streamlit, Plotly.

## Database design

A star schema:

- `fact_readings`: one row per city per hour with pollutant and weather measures. Primary key is (city_id, reading_time).
- `dim_city`: city, state, region, coordinates.
- `dim_date`: month, quarter, season, weekend flag.
- `pipeline_runs`: a log of every pipeline run.
- `daily_city_summary` (view): one row per city per day, counted only when at least 18 hours have valid PM2.5.

## Pipeline design

- **Extract:** two API calls per city (air quality and weather), with retries, back-off and handling of the API's rate limit.
- **Clean:** converts types, removes impossible values (such as negative concentrations), keeps humidity between 0 and 100, drops rows without PM2.5 and PM10, and removes duplicates.
- **Load:** batch upserts with `INSERT ... ON CONFLICT DO UPDATE`, so the pipeline is idempotent: running it twice gives the same result and never creates duplicates.
- **Resilience:** a failed city is logged and the others continue. The script exits with an error code so the automated run is flagged.
- **Late data:** the weather archive lags a few days, so the daily job re-fetches the last 7 days and fills the gaps.

## Automation

A scheduled GitHub Actions workflow (`.github/workflows/daily.yml`) runs every day at 02:30 UTC (08:00 IST) and can also be started manually. The database URL is stored as an encrypted GitHub secret, never in the code.

## SQL analysis

`sql/analysis.sql` contains the daily summary view and queries for: city ranking (`RANK`), share of days above the limits (`FILTER`), seasonal comparison (join to `dim_date`), month-over-month change (`LAG`), 7-day rolling averages (window frame), worst day per city (`ROW_NUMBER`), the most extreme days with their weather, longest unsafe streaks (gaps and islands), weather correlations (`CORR`) and year-over-year change.

## Dashboard

The Streamlit dashboard (`dashboard/app.py`) has summary cards, a city ranking with the annual standards, the share of days above the limits, a 7-day trend by city, a city-by-season heatmap, weather-versus-pollution scatter plots with correlation, and key insights calculated from the current filters. Live app: YOUR_DASHBOARD_LINK

## Project structure

```
pipeline/    config, fetch, clean, load, run, setup_db
sql/         schema.sql, analysis.sql, checks.sql
dashboard/   app.py, metrics.py
.github/workflows/daily.yml
```

## Run it locally

```
pip install -r requirements.txt
# create a .env file containing: DATABASE_URL=your PostgreSQL connection string
python -m pipeline.setup_db        # create tables (once)
python -m pipeline.run             # load history (safe to re-run)
python -m pipeline.run --days 7    # daily-style refresh
streamlit run dashboard/app.py
```

## Limitations

- Air quality values are **model-based estimates** (CAMS, via Open-Meteo) for each city's coordinates, not readings from ground sensors such as CPCB stations.
- The source provides US and European AQI, not India's CPCB AQI, so unsafe-day analysis uses raw PM2.5 concentrations against the NAAQS and WHO limits.
- History starts in January 2023, so trends are short-term.
- A streak ends if a single day falls below the limit, so streak length understates how persistent the pollution was.
- Correlations between weather and pollution do not prove cause and effect: season affects both.

## Data source

Air quality and weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0).
