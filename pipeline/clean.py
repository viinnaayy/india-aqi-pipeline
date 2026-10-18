"""TRANSFORM: fix types and remove impossible values before loading."""
import numpy as np
import pandas as pd

POLLUTANTS = ["pm2_5", "pm10", "no2", "so2", "co", "o3"]
NUMERIC_COLS = POLLUTANTS + ["us_aqi", "temperature", "humidity",
                             "wind_speed", "precipitation"]


def clean(df):
    df = df.copy()
    df["reading_time"] = pd.to_datetime(df["reading_time"])

    # make sure every measurement column is a number
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # concentrations, AQI, wind and rain can never be negative
    for col in POLLUTANTS + ["us_aqi", "wind_speed", "precipitation"]:
        df.loc[df[col] < 0, col] = np.nan

    # humidity is a percentage
    df["humidity"] = df["humidity"].where(df["humidity"].between(0, 100))

    # a row with no PM2.5 and no PM10 is useless for our analysis
    df = df.dropna(subset=["pm2_5", "pm10"], how="all")

    # one row per city per hour
    df = df.drop_duplicates(subset=["city_id", "reading_time"], keep="last")
    return df.sort_values(["city_id", "reading_time"]).reset_index(drop=True)
