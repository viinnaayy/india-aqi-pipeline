"""Pure-pandas helpers for the dashboard (no Streamlit here, so they are easy to test)."""
import pandas as pd

NAAQS = 60   # India 24-hour PM2.5 limit, ug/m3
WHO = 15     # WHO 2021 24-hour PM2.5 guideline, ug/m3
ANNUAL_NAAQS = 40  # India annual PM2.5 standard, ug/m3 (used for long-term averages)
WHO_ANNUAL = 5     # WHO 2021 annual PM2.5 guideline, ug/m3

SEASON_ORDER = ["Winter", "Summer", "Monsoon", "Post-monsoon"]
SEASON_MAP = {12: "Winter", 1: "Winter", 2: "Winter",
              3: "Summer", 4: "Summer", 5: "Summer",
              6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
              10: "Post-monsoon", 11: "Post-monsoon"}


def add_season(df):
    out = df.copy()
    out["season"] = out["obs_date"].dt.month.map(SEASON_MAP)
    return out


def city_summary(d):
    """One row per city: average PM2.5 and % of days above each limit."""
    g = d.groupby("city_name")["pm2_5"]
    return pd.DataFrame({
        "avg_pm25": g.mean(),
        "days": g.size(),
        "pct_above_naaqs": g.apply(lambda s: (s > NAAQS).mean() * 100),
        "pct_above_who": g.apply(lambda s: (s > WHO).mean() * 100),
    }).reset_index()


def add_rolling(d, window=7):
    """Add a 7-day rolling average of PM2.5 for each city."""
    out = d.sort_values(["city_name", "obs_date"]).copy()
    out["pm2_5_7day"] = out.groupby("city_name")["pm2_5"].transform(
        lambda s: s.rolling(window, min_periods=1).mean())
    return out


def season_pivot(d):
    """City x season table of average PM2.5, worst winter first."""
    p = d.pivot_table(index="city_name", columns="season", values="pm2_5", aggfunc="mean")
    p = p.reindex(columns=SEASON_ORDER)
    return p.sort_values("Winter", ascending=False)


def build_insights(d, summary):
    """Plain-English findings computed from whatever is currently selected."""
    top = summary.sort_values("avg_pm25", ascending=False).iloc[0]
    low = summary.sort_values("avg_pm25").iloc[0]
    worst = d.loc[d["pm2_5"].idxmax()]
    season = d.groupby("season")["pm2_5"].mean().idxmax()
    return [
        f"**{top['city_name']}** has the highest average PM2.5 ({top['avg_pm25']:.0f} ug/m3): "
        f"about {top['avg_pm25'] / ANNUAL_NAAQS:.1f}x India's annual standard ({ANNUAL_NAAQS}) "
        f"and {top['avg_pm25'] / WHO_ANNUAL:.0f}x the WHO annual guideline ({WHO_ANNUAL}).",
        f"**{low['city_name']}** has the lowest average PM2.5 ({low['avg_pm25']:.0f} ug/m3).",
        f"{top['pct_above_naaqs']:.0f}% of days in {top['city_name']} were above the India NAAQS limit of {NAAQS} ug/m3.",
        f"The most polluted season across the selected period is **{season}**.",
        f"Worst single day: **{worst['city_name']}** on {worst['obs_date']:%d %b %Y} "
        f"({worst['pm2_5']:.0f} ug/m3).",
    ]
