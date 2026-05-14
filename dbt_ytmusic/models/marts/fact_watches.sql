-- fact_watches.sql
-- Central fact table: one row per YouTube Music watch event

WITH watches   AS (SELECT * FROM {{ ref('stg_yt_history') }}),
     channels  AS (SELECT * FROM {{ ref('dim_channels') }}),
     videos    AS (SELECT * FROM {{ ref('dim_videos') }}),
     times     AS (SELECT * FROM {{ ref('dim_time') }})

SELECT
    -- Keys
    w.watch_id,
    c.channel_id,
    v.video_id_dim                          AS video_id,
    t.time_id,

    -- Denormalised for convenience
    w.video_title,
    w.channel_name,
    w.genre,
    w.watched_at,
    w.watched_date,
    w.device,
    w.time_of_day,

    -- Playback metrics
    w.watch_sec,
    w.watch_min,
    w.duration_sec,
    w.watch_pct,

    -- Behaviour flags
    w.is_skipped,
    w.is_full_listen,

    -- Derived metrics
    CASE WHEN w.is_skipped    THEN 1 ELSE 0 END  AS skip_count,
    CASE WHEN w.is_full_listen THEN 1 ELSE 0 END AS full_listen_count,

    -- Estimated ad revenue (YT Music pays ~$0.002/stream for ad-supported)
    -- YT Premium streams earn slightly more (~$0.008)
    ROUND(0.002 * (w.watch_pct / 100.0), 6)      AS est_ad_revenue_usd

FROM watches w
LEFT JOIN channels c ON c.channel_name = w.channel_name
LEFT JOIN videos   v ON v.video_title  = w.video_title
                     AND v.channel_name = w.channel_name
LEFT JOIN times    t ON t.watched_at   = w.watched_at
