-- dim_time.sql
-- Rich time dimension for time-intelligence queries

WITH spine AS (
    SELECT DISTINCT watched_at FROM {{ ref('stg_yt_history') }}
    WHERE watched_at IS NOT NULL
)

SELECT
    md5(CAST(watched_at AS VARCHAR))        AS time_id,
    watched_at,
    DATE(watched_at)                        AS date_day,
    HOUR(watched_at)                        AS hour_of_day,
    CASE
        WHEN HOUR(watched_at) BETWEEN 5  AND 11 THEN 'Morning'
        WHEN HOUR(watched_at) BETWEEN 12 AND 16 THEN 'Afternoon'
        WHEN HOUR(watched_at) BETWEEN 17 AND 20 THEN 'Evening'
        ELSE 'Night'
    END                                     AS time_of_day,
    DAYOFWEEK(watched_at)                   AS day_of_week_num,
    DAYNAME(watched_at)                     AS day_name,
    CASE WHEN DAYOFWEEK(watched_at) IN (1,7)
         THEN true ELSE false END           AS is_weekend,
    DAY(watched_at)                         AS day_of_month,
    MONTH(watched_at)                       AS month_num,
    MONTHNAME(watched_at)                   AS month_name,
    QUARTER(watched_at)                     AS quarter,
    YEAR(watched_at)                        AS year,
    WEEKOFYEAR(watched_at)                  AS week_of_year

FROM spine
