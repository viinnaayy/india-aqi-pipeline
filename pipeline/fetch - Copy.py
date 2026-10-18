"""EXTRACT: download hourly air quality + weather for one city from Open-Meteo."""
import time

import pandas as pd
import requests

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WX_URL = "https://archive-api.open-meteo.com/v1/archive"

AQ_VARS = ["pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide",
           "sulphur_dioxide", "ozone", "us_aqi"]
WX_VARS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation"]

# API names -> our database column names
RENAME = {
    "carbon_monoxide": "co",
    "nitrogen_dioxide": "no2",
    "sulphur_dioxide": "so2",
    "ozone": "o3",
    "temperature_2m": "temperature",
    "relative_humidity_2m": "humidity",
    "wind_speed_10m": "wind_speed",
}


def _get(url, params, retries=3):
    """Call the API; if it fails, wait and retry (2s, 4s, ...) before giving up."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)


def fetch_city(lat, lon, start_date, end_date):
    """Return one DataFrame with hourly air quality + weather for a city."""
    common = {"latitude": lat, "longitude": lon, "start_date": start_date,
              "end_date": end_date, "timezone": "Asia/Kolkata"}

    aq = _get(AQ_URL, {**common, "hourly": ",".join(AQ_VARS)})
    wx = _get(WX_URL, {**common, "hourly": ",".join(WX_VARS)})

    aq_df = pd.DataFrame(aq["hourly"])
    wx_df = pd.DataFrame(wx["hourly"])

    # LEFT join: keep every air quality hour, even if weather isn't published yet
    # (the weather archive lags a few days behind). Later runs fill the gaps.
    df = aq_df.merge(wx_df, on="time", how="left")
    df = df.rename(columns=RENAME)
    df["reading_time"] = pd.to_datetime(df.pop("time"))
    return df
