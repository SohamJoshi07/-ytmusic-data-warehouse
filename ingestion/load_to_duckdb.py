"""
load_to_duckdb.py
──────────────────
Ingests YouTube Music watch history JSON (Google Takeout format)
into DuckDB raw schema.

Handles both:
  - Sample data (with _prefixed helper fields)
  - Real Google Takeout watch-history.json
"""

import duckdb, pandas as pd, json, glob, os, re

DB_PATH        = "data/ytmusic.duckdb"
RAW_GLOB       = "data/raw/*.json"
MIN_WATCH_SEC  = 30   # filter out accidental plays under 30 seconds


def parse_entry(r: dict) -> dict | None:
    """Normalise a single Takeout record into a flat dict."""
    # Skip non-music entries
    if "YouTube Music" not in str(r.get("products", [])) and \
       "YouTube Music" not in str(r.get("header", "")):
        return None

    title_raw = r.get("title", "")
    # Strip "Watched " prefix
    video_title = re.sub(r"^Watched\s+", "", title_raw).strip()
    if not video_title:
        return None

    # Channel name from subtitles array
    subtitles  = r.get("subtitles", [])
    channel    = subtitles[0]["name"] if subtitles else "Unknown"
    video_url  = r.get("titleUrl", "")
    video_id   = re.search(r"v=([^&]+)", video_url)
    video_id   = video_id.group(1) if video_id else None

    # Timestamp
    ts_str = r.get("time", "")
    try:
        ts = pd.to_datetime(ts_str, utc=True)
    except Exception:
        return None

    # Sample data has helper fields; real Takeout does not
    duration_sec = r.get("_duration_sec", None)
    watch_sec    = r.get("_watch_sec", None)
    watch_pct    = r.get("_watch_pct", None)
    genre        = r.get("_genre", None)
    device       = r.get("_device", "UNKNOWN")
    skipped      = r.get("_skipped", None)

    return {
        "video_title":   video_title,
        "channel_name":  channel,
        "video_id":      video_id,
        "video_url":     video_url,
        "watched_at":    ts,
        "duration_sec":  duration_sec,
        "watch_sec":     watch_sec,
        "watch_pct":     watch_pct,
        "genre":         genre,
        "device":        device,
        "skipped":       skipped,
    }


def load_json(glob_pattern: str) -> pd.DataFrame:
    files = glob.glob(glob_pattern)
    if not files:
        raise FileNotFoundError(
            f"No JSON files at {glob_pattern}\n"
            "→ Run: python scripts/generate_sample_data.py"
        )
    records = []
    for f in files:
        print(f"  📂 {f}")
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
        parsed = [parse_entry(r) for r in data]
        records.extend([p for p in parsed if p])
    print(f"  ✅ Parsed {len(records):,} valid records")
    return pd.DataFrame(records)


def write_duckdb(df: pd.DataFrame):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("DROP TABLE IF EXISTS raw.yt_history")
    con.execute("CREATE TABLE raw.yt_history AS SELECT * FROM df")

    summary = con.execute("""
        SELECT
            COUNT(*)                             AS total_records,
            COUNT(DISTINCT channel_name)         AS unique_channels,
            COUNT(DISTINCT video_title)          AS unique_videos,
            ROUND(SUM(watch_sec)/3600.0, 1)      AS total_hours_watched
        FROM raw.yt_history
        WHERE watch_sec IS NOT NULL
    """).df()

    print("\n  📊 Summary:")
    print(summary.to_string(index=False))
    con.close()


if __name__ == "__main__":
    print("🎵 YT Music DWH — Ingestion")
    print("=" * 38)
    print(f"\n→ Loading from {RAW_GLOB}")
    df = load_json(RAW_GLOB)
    print(f"\n→ Writing to {DB_PATH}")
    write_duckdb(df)
    print("\n🎉 Done! Run: cd dbt_ytmusic && dbt run --profiles-dir .")
