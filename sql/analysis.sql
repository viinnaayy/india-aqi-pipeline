-- =====================================================================
-- DAY 4: SQL ANALYSIS  (run in the Neon SQL Editor, ONE block at a time)
-- =====================================================================
-- Limits used for "unsafe air" (24-hour average PM2.5, in ug/m3):
--   India NAAQS = 60      WHO 2021 guideline = 15

-- ---------------------------------------------------------------------
-- STEP 0: Daily summary view. Run this FIRST, once.
-- Turns ~650,000 hourly rows into one row per city per day.
-- A day counts only if it has at least 18 valid PM2.5 hours, so partial
-- days never distort the averages.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW daily_city_summary AS
SELECT f.city_id,
       c.city_name,
       c.region,
       f.reading_time::date                 AS obs_date,
       AVG(f.pm2_5)::numeric(8,2)           AS pm2_5_avg,
       MAX(f.pm2_5)::numeric(8,2)           AS pm2_5_max,
       AVG(f.pm10)::numeric(8,2)            AS pm10_avg,
       AVG(f.us_aqi)::numeric(8,2)          AS aqi_avg,
       MAX(f.us_aqi)::numeric(8,2)          AS aqi_max,
       AVG(f.temperature)::numeric(8,2)     AS temp_avg,
       AVG(f.humidity)::numeric(8,2)        AS humidity_avg,
       AVG(f.wind_speed)::numeric(8,2)      AS wind_avg,
       SUM(f.precipitation)::numeric(8,2)   AS rain_total,
       COUNT(f.pm2_5)                       AS hours_recorded
FROM fact_readings f
JOIN dim_city c ON c.city_id = f.city_id
GROUP BY f.city_id, c.city_name, c.region, f.reading_time::date
HAVING COUNT(f.pm2_5) >= 18;

-- Quick check: should return one row per city per day (about 27,000 rows)
-- SELECT COUNT(*) FROM daily_city_summary;


-- ---------------------------------------------------------------------
-- Q1. Which cities are the most polluted overall?   [RANK window function]
-- Interview: "RANK() numbers rows by pollution level; ties share a rank."
-- ---------------------------------------------------------------------
SELECT city_name,
       ROUND(AVG(pm2_5_avg), 1)                      AS avg_pm2_5,
       RANK() OVER (ORDER BY AVG(pm2_5_avg) DESC)    AS pollution_rank
FROM daily_city_summary
GROUP BY city_name
ORDER BY pollution_rank;


-- ---------------------------------------------------------------------
-- Q2. What % of days exceed the safe limits?        [FILTER, conditional counts]
-- Interview: "I compared each city's DAILY average to the 24-hour
-- NAAQS and WHO limits, which is how those limits are defined."
-- ---------------------------------------------------------------------
SELECT city_name,
       COUNT(*)                                                           AS total_days,
       ROUND(100.0 * COUNT(*) FILTER (WHERE pm2_5_avg > 60) / COUNT(*), 1) AS pct_days_above_naaqs,
       ROUND(100.0 * COUNT(*) FILTER (WHERE pm2_5_avg > 15) / COUNT(*), 1) AS pct_days_above_who
FROM daily_city_summary
GROUP BY city_name
ORDER BY pct_days_above_naaqs DESC;


-- ---------------------------------------------------------------------
-- Q3. Which season is the worst, city by city?     [JOIN + pivot with FILTER]
-- Interview: "Joined the fact data to dim_date to get the season, then
-- pivoted seasons into columns using conditional aggregation."
-- ---------------------------------------------------------------------
SELECT s.city_name,
       ROUND(AVG(s.pm2_5_avg) FILTER (WHERE d.season = 'Winter'), 1)       AS winter,
       ROUND(AVG(s.pm2_5_avg) FILTER (WHERE d.season = 'Summer'), 1)       AS summer,
       ROUND(AVG(s.pm2_5_avg) FILTER (WHERE d.season = 'Monsoon'), 1)      AS monsoon,
       ROUND(AVG(s.pm2_5_avg) FILTER (WHERE d.season = 'Post-monsoon'), 1) AS post_monsoon
FROM daily_city_summary s
JOIN dim_date d ON d.date_id = s.obs_date
GROUP BY s.city_name
ORDER BY winter DESC;


-- ---------------------------------------------------------------------
-- Q4. How did one city change month over month?    [CTE + LAG]
-- Change 'Delhi' to any city. LAG looks at the previous row in the group.
-- ---------------------------------------------------------------------
WITH monthly AS (
    SELECT city_name,
           DATE_TRUNC('month', obs_date::timestamp)::date AS month_start,
           AVG(pm2_5_avg)                                 AS avg_pm2_5
    FROM daily_city_summary
    GROUP BY 1, 2
)
SELECT city_name,
       month_start,
       ROUND(avg_pm2_5, 1) AS avg_pm2_5,
       ROUND(avg_pm2_5 - LAG(avg_pm2_5) OVER (PARTITION BY city_name ORDER BY month_start), 1)
           AS change_vs_prev_month
FROM monthly
WHERE city_name = 'Delhi'
ORDER BY month_start;


-- ---------------------------------------------------------------------
-- Q5. 7-day rolling average, to smooth out daily noise.   [window frame]
-- The window is computed first (inside the CTE), THEN filtered, so the
-- first rows of the date range still get a full 7-day window.
-- ---------------------------------------------------------------------
WITH rolling AS (
    SELECT city_name,
           obs_date,
           pm2_5_avg,
           AVG(pm2_5_avg) OVER (PARTITION BY city_name
                                ORDER BY obs_date
                                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS pm2_5_7day
    FROM daily_city_summary
)
SELECT city_name, obs_date,
       pm2_5_avg                AS pm2_5_daily,
       ROUND(pm2_5_7day, 1)     AS pm2_5_7day_avg
FROM rolling
WHERE city_name = 'Delhi' AND obs_date >= '2025-10-01'
ORDER BY obs_date;


-- ---------------------------------------------------------------------
-- Q6. The single worst day for each city.          [ROW_NUMBER, top-1 per group]
-- Interview: "RANK vs DENSE_RANK vs ROW_NUMBER: ROW_NUMBER never ties,
-- so it gives exactly one row per city."
-- ---------------------------------------------------------------------
SELECT city_name, obs_date, pm2_5_avg, aqi_max
FROM (
    SELECT city_name, obs_date, pm2_5_avg, aqi_max,
           ROW_NUMBER() OVER (PARTITION BY city_name ORDER BY pm2_5_avg DESC) AS rn
    FROM daily_city_summary
) t
WHERE rn = 1
ORDER BY pm2_5_avg DESC;


-- ---------------------------------------------------------------------
-- Q7. The 10 most extreme days overall, and the weather behind them.
-- (Answers problem-statement question 5.)
-- ---------------------------------------------------------------------
SELECT city_name, obs_date,
       ROUND(pm2_5_avg, 0)    AS pm2_5,
       ROUND(wind_avg, 1)     AS wind_kmh,
       ROUND(temp_avg, 1)     AS temp_c,
       ROUND(humidity_avg, 0) AS humidity_pct
FROM daily_city_summary
ORDER BY pm2_5_avg DESC
LIMIT 10;


-- ---------------------------------------------------------------------
-- Q8. Longest run of consecutive days above the NAAQS limit.
-- [gaps-and-islands: date minus row number stays constant inside a streak]
-- Interview: "Consecutive dates minus an increasing row number give the
-- same value, so grouping by it finds each streak."
-- ---------------------------------------------------------------------
WITH bad_days AS (
    SELECT city_name, obs_date,
           obs_date - (ROW_NUMBER() OVER (PARTITION BY city_name ORDER BY obs_date))::int AS grp
    FROM daily_city_summary
    WHERE pm2_5_avg > 60
),
streaks AS (
    SELECT city_name, grp,
           COUNT(*)      AS streak_days,
           MIN(obs_date) AS start_date,
           MAX(obs_date) AS end_date
    FROM bad_days
    GROUP BY city_name, grp
)
SELECT city_name, streak_days, start_date, end_date
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY city_name ORDER BY streak_days DESC) AS rn
    FROM streaks
) t
WHERE rn = 1
ORDER BY streak_days DESC;


-- ---------------------------------------------------------------------
-- Q9. How does weather relate to PM2.5?            [CORR]
-- Values run from -1 to +1. Negative wind correlation = calmer air,
-- more pollution. REMEMBER: correlation is not causation (season is a
-- confounder: cold, calm winters are bad for several reasons at once).
-- ---------------------------------------------------------------------
SELECT city_name,
       ROUND(CORR(pm2_5_avg, wind_avg)::numeric, 2)     AS corr_wind,
       ROUND(CORR(pm2_5_avg, temp_avg)::numeric, 2)     AS corr_temp,
       ROUND(CORR(pm2_5_avg, humidity_avg)::numeric, 2) AS corr_humidity,
       ROUND(CORR(pm2_5_avg, rain_total)::numeric, 2)   AS corr_rain
FROM daily_city_summary
GROUP BY city_name
ORDER BY corr_wind;


-- ---------------------------------------------------------------------
-- Q10. Is the air getting better or worse year over year?  [LAG on years]
-- Only full years (2023 to 2025) are compared, so the partial 2026
-- doesn't distort the trend.
-- ---------------------------------------------------------------------
WITH yearly AS (
    SELECT city_name,
           EXTRACT(YEAR FROM obs_date)::int AS yr,
           AVG(pm2_5_avg)                   AS avg_pm2_5
    FROM daily_city_summary
    WHERE obs_date < '2026-01-01'
    GROUP BY 1, 2
)
SELECT city_name, yr,
       ROUND(avg_pm2_5, 1) AS avg_pm2_5,
       ROUND(100.0 * (avg_pm2_5 - LAG(avg_pm2_5) OVER (PARTITION BY city_name ORDER BY yr))
             / LAG(avg_pm2_5) OVER (PARTITION BY city_name ORDER BY yr), 1) AS pct_change_vs_prev_year
FROM yearly
ORDER BY city_name, yr;
