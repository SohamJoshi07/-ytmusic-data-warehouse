-- mart_listening_patterns.sql
-- Hour x Day heatmap data for dashboard

SELECT
    dt.hour_of_day,
    dt.day_name,
    dt.day_of_week_num,
    dt.time_of_day,
    dt.is_weekend,
    COUNT(*)                                         AS play_count,
    ROUND(SUM(f.watch_min), 1)                       AS total_minutes,
    ROUND(AVG(f.watch_min), 2)                       AS avg_minutes,
    ROUND(100.0 * SUM(f.skip_count) / COUNT(*), 1) AS skip_rate_pct,
    ROUND(AVG(f.watch_pct), 1)                       AS avg_watch_pct

FROM {{ ref('fact_watches') }} f
JOIN {{ ref('dim_time') }} dt ON dt.time_id = f.time_id
GROUP BY dt.hour_of_day, dt.day_name, dt.day_of_week_num, dt.time_of_day, dt.is_weekend
ORDER BY dt.day_of_week_num, dt.hour_of_day
