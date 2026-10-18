-- Star schema: 1 fact table (hourly readings) + 2 dimensions (city, date)

CREATE TABLE IF NOT EXISTS dim_city (
    city_id    SERIAL PRIMARY KEY,
    city_name  TEXT UNIQUE NOT NULL,
    state      TEXT NOT NULL,
    region     TEXT NOT NULL,
    latitude   NUMERIC(8,4) NOT NULL,
    longitude  NUMERIC(8,4) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id     DATE PRIMARY KEY,
    year        INT  NOT NULL,
    month       INT  NOT NULL,
    month_name  TEXT NOT NULL,
    quarter     INT  NOT NULL,
    season      TEXT NOT NULL,      -- Winter / Summer / Monsoon / Post-monsoon
    is_weekend  BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_readings (
    city_id        INT       NOT NULL REFERENCES dim_city(city_id),
    reading_time   TIMESTAMP NOT NULL,   -- local India time (IST)
    pm2_5          REAL,   -- ug/m3
    pm10           REAL,
    no2            REAL,
    so2            REAL,
    co             REAL,
    o3             REAL,
    us_aqi         REAL,
    temperature    REAL,   -- deg C
    humidity       REAL,   -- %
    wind_speed     REAL,   -- km/h
    precipitation  REAL,   -- mm
    PRIMARY KEY (city_id, reading_time)   -- prevents duplicate rows
);

CREATE INDEX IF NOT EXISTS idx_fact_reading_time ON fact_readings (reading_time);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id       SERIAL PRIMARY KEY,
    run_time     TIMESTAMP DEFAULT NOW(),
    city_name    TEXT,
    rows_loaded  INT,
    status       TEXT,
    error        TEXT
);

-- Fill the date dimension (2023 to 2030). Safe to re-run.
INSERT INTO dim_date
SELECT d::date,
       EXTRACT(YEAR    FROM d)::int,
       EXTRACT(MONTH   FROM d)::int,
       TO_CHAR(d, 'Mon'),
       EXTRACT(QUARTER FROM d)::int,
       CASE WHEN EXTRACT(MONTH FROM d) IN (12, 1, 2)    THEN 'Winter'
            WHEN EXTRACT(MONTH FROM d) IN (3, 4, 5)     THEN 'Summer'
            WHEN EXTRACT(MONTH FROM d) IN (6, 7, 8, 9)  THEN 'Monsoon'
            ELSE 'Post-monsoon' END,
       EXTRACT(ISODOW FROM d) IN (6, 7)
FROM generate_series('2023-01-01'::date, '2030-12-31'::date, interval '1 day') AS d
ON CONFLICT (date_id) DO NOTHING;
