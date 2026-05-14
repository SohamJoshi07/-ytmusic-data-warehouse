-- mart_monthly_trends.sql

SELECT
    dt.year,
    dt.month_num,
    dt.month_name,
    CAST(dt.year AS VARCHAR) || '-' || LPAD(CAST(dt.month_num AS VARCHAR),2,'0') AS year_month,
    COUNT(*)                                          AS total_plays,
    COUNT(DISTINCT f.channel_name)                    AS unique_channels,
    COUNT(DISTINCT f.video_title)                     AS unique_videos,
    ROUND(SUM(f.watch_min), 1)                        AS total_minutes,
    ROUND(SUM(f.watch_min) / 60.0, 2)               AS total_hours,
    ROUND(AVG(f.watch_min), 2)                        AS avg_min_per_play,
    ROUND(AVG(f.watch_pct), 1)                        AS avg_watch_pct,
    SUM(f.skip_count)                                 AS total_skips,
    ROUND(100.0 * SUM(f.skip_count) / COUNT(*), 1)  AS skip_rate_pct,
    ROUND(SUM(f.est_ad_revenue_usd), 4)               AS est_ad_revenue_usd

FROM {{ ref('fact_watches') }} f
JOIN {{ ref('dim_time') }} dt ON dt.time_id = f.time_id
GROUP BY dt.year, dt.month_num, dt.month_name
ORDER BY dt.year, dt.month_num
