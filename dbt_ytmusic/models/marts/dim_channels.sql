-- dim_channels.sql
-- One row per unique YouTube Music channel (artist)

WITH channels AS (
    SELECT DISTINCT
        md5(channel_name)  AS channel_id,
        channel_name,
        COUNT(*)  OVER (PARTITION BY channel_name) AS total_plays
    FROM {{ ref('stg_yt_history') }}
    WHERE channel_name IS NOT NULL
)

SELECT DISTINCT channel_id, channel_name
FROM channels
ORDER BY channel_name
