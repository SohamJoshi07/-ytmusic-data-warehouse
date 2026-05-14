-- mart_channel_summary.sql
-- Pre-aggregated channel (artist) level analytics

SELECT
    channel_name,
    genre,
    COUNT(*)                                                   AS total_plays,
    COUNT(DISTINCT video_title)                                AS unique_videos,
    COUNT(DISTINCT watched_date)                               AS active_days,
    ROUND(SUM(watch_min), 1)                                   AS total_minutes,
    ROUND(SUM(watch_min) / 60.0, 2)                           AS total_hours,
    ROUND(AVG(watch_min), 2)                                   AS avg_min_per_play,
    ROUND(AVG(watch_pct), 1)                                   AS avg_watch_pct,
    SUM(skip_count)                                            AS total_skips,
    ROUND(100.0 * SUM(skip_count) / COUNT(*), 1)             AS skip_rate_pct,
    SUM(full_listen_count)                                     AS full_listens,
    ROUND(100.0 * SUM(full_listen_count) / COUNT(*), 1)      AS full_listen_pct,
    ROUND(SUM(est_ad_revenue_usd), 4)                         AS est_ad_revenue_usd,
    MIN(watched_at)                                            AS first_watched,
    MAX(watched_at)                                            AS last_watched

FROM {{ ref('fact_watches') }}
GROUP BY channel_name, genre
ORDER BY total_hours DESC
