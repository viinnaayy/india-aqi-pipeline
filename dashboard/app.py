"""India Air Quality dashboard.

Run locally from the project folder:
    py -m streamlit run dashboard/app.py
"""
import os

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from dotenv import load_dotenv

from metrics import (ANNUAL_NAAQS, NAAQS, WHO, WHO_ANNUAL, SEASON_ORDER, add_rolling, add_season,
                     build_insights, city_summary, season_pivot)

st.set_page_config(page_title="India Air Quality", page_icon="🌫️", layout="wide")


# ---------- data access ----------
def get_db_url():
    """On Streamlit Cloud the URL comes from Secrets; locally it comes from .env."""
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        load_dotenv()
        return os.environ["DATABASE_URL"]


def run_query(sql):
    conn = psycopg2.connect(get_db_url())
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [c[0] for c in cur.description]
            rows = cur.fetchall()
    finally:
        conn.close()
    return pd.DataFrame(rows, columns=cols)


@st.cache_data(ttl=3600, show_spinner="Loading data from the database...")
def load_daily():
    df = run_query("""
        SELECT city_name, region, obs_date,
               pm2_5_avg::float   AS pm2_5,
               aqi_max::float     AS aqi_max,
               temp_avg::float    AS temp,
               humidity_avg::float AS humidity,
               wind_avg::float    AS wind,
               rain_total::float  AS rain
        FROM daily_city_summary
        ORDER BY city_name, obs_date
    """)
    df["obs_date"] = pd.to_datetime(df["obs_date"])
    return add_season(df)


@st.cache_data(ttl=600)
def last_pipeline_run():
    df = run_query("SELECT MAX(run_time) AS t FROM pipeline_runs WHERE status = 'success'")
    return df["t"].iloc[0]


# ---------- load + filters ----------
df = load_daily()
if df.empty:
    st.error("No data found. Run the pipeline first (py -m pipeline.run).")
    st.stop()

st.title("India Air Quality Dashboard")
last_run = last_pipeline_run()
last_run_text = f"{last_run:%d %b %Y, %H:%M} UTC" if pd.notna(last_run) else "n/a"
st.caption(f"20 Indian cities | data through {df['obs_date'].max():%d %b %Y} | "
           f"last pipeline run: {last_run_text}")

st.sidebar.header("Filters")
all_cities = sorted(df["city_name"].unique())
default_cities = [c for c in ["Delhi", "Mumbai", "Kolkata", "Chennai", "Bengaluru"] if c in all_cities]
cities = st.sidebar.multiselect("Cities (for the trend and weather charts)",
                                all_cities, default=default_cities)
min_d, max_d = df["obs_date"].min().date(), df["obs_date"].max().date()
rng = st.sidebar.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
if len(rng) != 2:
    st.info("Pick both a start date and an end date in the sidebar.")
    st.stop()

d = df[(df["obs_date"] >= pd.Timestamp(rng[0])) & (df["obs_date"] <= pd.Timestamp(rng[1]))]
if d.empty:
    st.warning("No data in that date range.")
    st.stop()
sel = d[d["city_name"].isin(cities)]
summary = city_summary(d)

# ---------- KPI cards ----------
top = summary.sort_values("avg_pm25", ascending=False).iloc[0]
low = summary.sort_values("avg_pm25").iloc[0]
worst = d.loc[d["pm2_5"].idxmax()]
share = (d["pm2_5"] > NAAQS).mean() * 100

k1, k2, k3, k4 = st.columns(4)
k1.metric("Most polluted city", top["city_name"], f"{top['avg_pm25']:.0f} ug/m3 avg", delta_color="off")
k2.metric("Cleanest city", low["city_name"], f"{low['avg_pm25']:.0f} ug/m3 avg", delta_color="off")
k3.metric("City-days above NAAQS", f"{share:.0f}%", f"limit {NAAQS} ug/m3", delta_color="off")
k4.metric("Worst single day", f"{worst['pm2_5']:.0f} ug/m3",
          f"{worst['city_name']}, {worst['obs_date']:%d %b %Y}", delta_color="off")

# ---------- row 1: ranking + exceedance ----------
c1, c2 = st.columns(2)
with c1:
    st.subheader("City ranking: average PM2.5")
    rank = summary.sort_values("avg_pm25")
    fig = px.bar(rank, x="avg_pm25", y="city_name", orientation="h",
                 color="avg_pm25", color_continuous_scale="YlOrRd",
                 labels={"avg_pm25": "Average PM2.5 (ug/m3)", "city_name": ""})
    fig.add_vline(x=ANNUAL_NAAQS, line_dash="dash", annotation_text=f"India annual {ANNUAL_NAAQS}")
    fig.add_vline(x=WHO_ANNUAL, line_dash="dot", annotation_text=f"WHO annual {WHO_ANNUAL}")
    fig.update_layout(coloraxis_showscale=False, height=520)
    st.plotly_chart(fig)

with c2:
    st.subheader("Share of days above the safe limit")
    long = summary.melt(id_vars="city_name",
                        value_vars=["pct_above_naaqs", "pct_above_who"],
                        var_name="limit", value_name="pct_days")
    long["limit"] = long["limit"].map({"pct_above_naaqs": f"India NAAQS ({NAAQS})",
                                       "pct_above_who": f"WHO ({WHO})"})
    order = summary.sort_values("pct_above_naaqs", ascending=False)["city_name"]
    fig = px.bar(long, x="city_name", y="pct_days", color="limit", barmode="group",
                 category_orders={"city_name": list(order)},
                 labels={"pct_days": "% of days", "city_name": ""})
    fig.update_layout(height=520, legend_title_text="")
    st.plotly_chart(fig)

# ---------- trend ----------
st.subheader("PM2.5 trend (7-day rolling average)")
if sel.empty:
    st.info("Select at least one city in the sidebar.")
else:
    roll = add_rolling(sel)
    fig = px.line(roll, x="obs_date", y="pm2_5_7day", color="city_name",
                  labels={"pm2_5_7day": "PM2.5 (ug/m3)", "obs_date": "", "city_name": "City"})
    fig.add_hline(y=NAAQS, line_dash="dash", annotation_text=f"NAAQS {NAAQS}")
    fig.add_hline(y=WHO, line_dash="dot", annotation_text=f"WHO {WHO}")
    fig.update_layout(height=420)
    st.plotly_chart(fig)

# ---------- seasons ----------
st.subheader("Seasonal pattern: average PM2.5 by city and season")
pivot = season_pivot(d)
fig = px.imshow(pivot, text_auto=".0f", aspect="auto", color_continuous_scale="YlOrRd",
                labels={"color": "PM2.5 (ug/m3)", "x": "", "y": ""})
fig.update_layout(height=620)
st.plotly_chart(fig)
st.caption("Seasons: Winter Dec-Feb, Summer Mar-May, Monsoon Jun-Sep, Post-monsoon Oct-Nov.")

# ---------- weather ----------
st.subheader("Weather vs PM2.5")
options = {"Wind speed (km/h)": "wind", "Temperature (C)": "temp",
           "Humidity (%)": "humidity", "Rain (mm/day)": "rain"}
label = st.selectbox("Weather factor", list(options))
col = options[label]
if sel.empty:
    st.info("Select at least one city in the sidebar.")
else:
    pts = sel.dropna(subset=[col, "pm2_5"])
    fig = px.scatter(pts, x=col, y="pm2_5", color="city_name", opacity=0.45,
                     labels={col: label, "pm2_5": "Daily PM2.5 (ug/m3)", "city_name": "City"})
    fig.update_layout(height=450)
    st.plotly_chart(fig)
    if len(pts) > 2:
        r = pts[["pm2_5", col]].corr().iloc[0, 1]
        st.caption(f"Correlation across the selected cities: {r:.2f}. "
                   "Correlation is not causation: season affects both weather and pollution.")

# ---------- insights + notes ----------
st.subheader("Key insights (calculated from the current filters)")
for line in build_insights(d, summary):
    st.markdown(f"- {line}")

with st.expander("About this data and its limitations"):
    st.markdown(
        "- Air quality values are **model-based estimates** (CAMS, via Open-Meteo), "
        "not readings from ground sensors such as CPCB stations.\n"
        "- Limits compare each city's **daily average** PM2.5 with the 24-hour India NAAQS "
        f"({NAAQS} ug/m3) and WHO 2021 ({WHO} ug/m3) values. Long-term averages are compared with "
        f"the annual standards (India {ANNUAL_NAAQS}, WHO {WHO_ANNUAL} ug/m3).\n"
        "- Air quality history covers only the last few years, so trends are short-term.\n"
        "- The data refreshes daily through an automated pipeline (GitHub Actions)."
    )

st.markdown("---")
st.caption("Data: air quality and weather by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0).")
