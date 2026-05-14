-- dim_videos.sql
-- One row per unique video

WITH videos AS (
    SELECT DISTINCT
        md5(video_title || '|' || channel_name) AS video_id_dim,
        video_title,
        channel_name,
        genre,
        FIRST(video_id)  AS yt_video_id,
        FIRST(video_url) AS video_url,
        AVG(duration_sec) AS avg_duration_sec
    FROM {{ ref('stg_yt_history') }}
    WHERE video_title IS NOT NULL
    GROUP BY video_title, channel_name, genre
)

SELECT * FROM videos
ORDER BY channel_name, video_title
