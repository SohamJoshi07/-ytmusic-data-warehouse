-- stg_yt_history.sql
-- Cleans and standardises raw YouTube Music watch history.
-- Filters out accidental plays, enriches with derived fields.

WITH source AS (
    SELECT * FROM {{ source('raw', 'yt_history') }}
),

cleaned AS (
    SELECT
        -- Unique watch ID
        md5(
            COALESCE(CAST(watched_at AS VARCHAR), '') ||
            COALESCE(video_title, '')                 ||
            COALESCE(channel_name, '')                ||
            COALESCE(CAST(watch_sec AS VARCHAR), '')
        ) AS watch_id,

        -- Timestamps
        CAST(watched_at AS TIMESTAMP)       AS watched_at,
        DATE(CAST(watched_at AS TIMESTAMP)) AS watched_date,

        -- Content metadata
        TRIM(video_title)                   AS video_title,
        TRIM(channel_name)                  AS channel_name,
        video_id,
        video_url,
        COALESCE(genre, 'Unknown')          AS genre,

        -- Playback metrics
        COALESCE(watch_sec, 0)              AS watch_sec,
        ROUND(COALESCE(watch_sec, 0) / 60.0, 3) AS watch_min,
        COALESCE(duration_sec, 0)           AS duration_sec,
        COALESCE(watch_pct, 0)              AS watch_pct,

        -- Behaviour flags
        -- YT Music: no explicit skip — infer from watch %
        CASE
            WHEN COALESCE(skipped, false) = true THEN true
            WHEN COALESCE(watch_pct, 0) < 45     THEN true
            ELSE false
        END                                 AS is_skipped,

        CASE
            WHEN COALESCE(watch_pct, 0) >= 80 THEN true
            ELSE false
        END                                 AS is_full_listen,

        device,

        -- Time-of-day bucket
        CASE
            WHEN HOUR(CAST(watched_at AS TIMESTAMP)) BETWEEN 5  AND 11 THEN 'Morning'
            WHEN HOUR(CAST(watched_at AS TIMESTAMP)) BETWEEN 12 AND 16 THEN 'Afternoon'
            WHEN HOUR(CAST(watched_at AS TIMESTAMP)) BETWEEN 17 AND 20 THEN 'Evening'
            ELSE 'Night'
        END AS time_of_day

    FROM source

    WHERE
        video_title IS NOT NULL
        AND channel_name IS NOT NULL
        -- Filter out plays under 30 seconds
        AND COALESCE(watch_sec, 0) >= 30
)

SELECT * FROM cleaned
