-- Run these in the Neon SQL editor after loading, to confirm the data is healthy.

-- 1) Total rows (expect roughly 650,000 after a full load)
SELECT COUNT(*) FROM fact_readings;

-- 2) Rows per city (every city should have a similar count)
SELECT c.city_name, COUNT(*) AS rows, MIN(f.reading_time) AS first_hour, MAX(f.reading_time) AS last_hour
FROM fact_readings f JOIN dim_city c USING (city_id)
GROUP BY c.city_name ORDER BY c.city_name;

-- 3) Null check: how many missing values per column?
SELECT COUNT(*) - COUNT(pm2_5) AS null_pm2_5,
       COUNT(*) - COUNT(us_aqi) AS null_aqi,
       COUNT(*) - COUNT(temperature) AS null_temp
FROM fact_readings;

-- 4) Did the pipeline run cleanly?
SELECT * FROM pipeline_runs ORDER BY run_id DESC LIMIT 25;
