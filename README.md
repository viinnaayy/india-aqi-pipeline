# India Air Quality Data Pipeline & Dashboard

## Problem statement
India has some of the most polluted cities in the world, but air quality data is scattered across sources, changes daily, and is hard to interpret. Most analyses are one-time snapshots that go out of date quickly.

This project builds an automated pipeline that collects hourly air quality and weather data for 20 Indian cities, stores it in a PostgreSQL star schema, and turns it into a dashboard that answers:

1. Which cities have the worst air quality, and how has it changed over time?
2. Which months and seasons are the most polluted?
3. How do temperature, wind speed, and humidity relate to pollution?
4. How many days per year does each city exceed the India NAAQS (PM2.5: 60 µg/m³) and WHO (15 µg/m³) 24-hour limits?
5. Which days were extreme outliers, and what were the conditions?

## Architecture
Open-Meteo APIs -> Python (fetch, clean) -> PostgreSQL (star schema) -> SQL analysis -> Streamlit dashboard
Daily refresh: GitHub Actions (added later)

## Tech stack
Python (pandas, requests), PostgreSQL (Neon), SQL, GitHub Actions, Streamlit

## Schema
- `dim_city`, `dim_date` (dimensions)
- `fact_readings` (hourly readings per city, primary key = city_id + reading_time)
- `pipeline_runs` (log of every pipeline run)

## How to run
1. `python -m venv venv` and activate it, then `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and paste your PostgreSQL connection string
3. `python -m pipeline.setup_db` (creates tables, run once)
4. `python -m pipeline.run` (loads history; safe to re-run)

## Key findings
_To be added after the analysis._

## Limitations
- Air quality values are model-based estimates (CAMS via Open-Meteo), not readings from ground sensors.
- The source provides US/European AQI, not India's CPCB AQI, so threshold analysis uses raw pollutant concentrations against NAAQS and WHO limits.
- Historical air quality data covers only the last few years.
