"""
generate_sample_data.py
────────────────────────
Generates realistic YouTube Music watch history data
mimicking the format from Google Takeout.

Output: data/raw/watch-history.json
"""

import json, random, os
from datetime import datetime, timedelta

# ── Music catalog
CATALOG = [
    # (video_title, channel_name, duration_sec, genre)
    ("Blinding Lights",          "The Weeknd",         200, "Pop"),
    ("Save Your Tears",          "The Weeknd",         215, "Pop"),
    ("Starboy",                  "The Weeknd",         230, "Pop"),
    ("Die For You",              "The Weeknd",         260, "Pop"),
    ("Anti-Hero",                "Taylor Swift",       200, "Pop"),
    ("Cruel Summer",             "Taylor Swift",       178, "Pop"),
    ("Lavender Haze",            "Taylor Swift",       202, "Pop"),
    ("Shake It Off",             "Taylor Swift",       219, "Pop"),
    ("bad guy",                  "Billie Eilish",      194, "Electropop"),
    ("Happier Than Ever",        "Billie Eilish",      298, "Electropop"),
    ("Therefore I Am",           "Billie Eilish",      174, "Electropop"),
    ("As It Was",                "Harry Styles",       167, "Pop"),
    ("Watermelon Sugar",         "Harry Styles",       174, "Pop"),
    ("Golden",                   "Harry Styles",       208, "Pop"),
    ("Levitating",               "Dua Lipa",           203, "Dance-Pop"),
    ("Dont Start Now",           "Dua Lipa",           183, "Dance-Pop"),
    ("Physical",                 "Dua Lipa",           193, "Dance-Pop"),
    ("drivers license",          "Olivia Rodrigo",     242, "Pop"),
    ("good 4 u",                 "Olivia Rodrigo",     178, "Pop-Punk"),
    ("vampire",                  "Olivia Rodrigo",     219, "Pop"),
    ("Heat Waves",               "Glass Animals",      238, "Indie-Pop"),
    ("Mr. Rager",                "Kid Cudi",           261, "Hip-Hop"),
    ("HUMBLE.",                  "Kendrick Lamar",     177, "Hip-Hop"),
    ("DNA.",                     "Kendrick Lamar",     185, "Hip-Hop"),
    ("Not Like Us",              "Kendrick Lamar",     274, "Hip-Hop"),
    ("Industry Baby",            "Lil Nas X",          212, "Hip-Hop"),
    ("MONTERO",                  "Lil Nas X",          137, "Pop"),
    ("Flowers",                  "Miley Cyrus",        200, "Pop"),
    ("Unholy",                   "Sam Smith",          156, "Pop"),
    ("Stay",                     "The Kid LAROI",      141, "Pop"),
    ("Golden Hour",              "JVKE",               170, "Pop"),
    ("Calm Down",                "Rema",               240, "Afrobeats"),
    ("Running Up That Hill",     "Kate Bush",          300, "Synth-Pop"),
    ("About Damn Time",          "Lizzo",              193, "Funk-Pop"),
    ("Lift Me Up",               "Rihanna",            188, "R&B"),
    ("Peaches",                  "Justin Bieber",      198, "R&B"),
    ("Ghost",                    "Justin Bieber",      153, "Pop"),
    ("MIDDLE CHILD",             "J. Cole",            243, "Hip-Hop"),
    ("Escapism.",                "RAYE",               213, "R&B"),
    ("Creepin",                  "Metro Boomin",       217, "Hip-Hop"),
]

HOUR_WEIGHTS = [1,1,1,1,1,1,2,3,3,2,2,2,2,2,2,2,3,4,5,6,6,5,4,2]
DEVICES = ["MOBILE","COMPUTER","TABLET","TV","MOBILE","MOBILE","COMPUTER"]


def make_entry(ts: datetime, idx: int) -> dict:
    title, channel, dur_sec, genre = CATALOG[idx]
    # watch percentage: 70–100% for full listens, 15–40% for skips
    skipped = random.random() < 0.14
    watch_pct = random.uniform(0.15, 0.40) if skipped else random.uniform(0.70, 1.00)
    watch_sec = int(dur_sec * watch_pct)

    return {
        "header": "YouTube Music",
        "title": f"Watched {title}",
        "titleUrl": f"https://www.youtube.com/watch?v={''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',k=11))}",
        "subtitles": [{"name": channel, "url": f"https://www.youtube.com/channel/UC{''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789',k=22))}"}],
        "time": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "products": ["YouTube Music"],
        "activityControls": ["YouTube watch history"],
        # Extra fields we derive
        "_video_title": title,
        "_channel_name": channel,
        "_duration_sec": dur_sec,
        "_watch_sec": watch_sec,
        "_watch_pct": round(watch_pct * 100, 1),
        "_genre": genre,
        "_device": random.choice(DEVICES),
        "_skipped": skipped,
    }


def generate(n=2200):
    records = []
    start = datetime.now() - timedelta(days=730)
    ts = start

    while len(records) < n:
        hour = random.choices(range(24), weights=HOUR_WEIGHTS)[0]
        ts = ts + timedelta(minutes=random.randint(1, 160))
        ts = ts.replace(hour=hour, minute=random.randint(0, 59))

        # Binge phase — same artist back to back
        if random.random() < 0.12:
            binge_artist = random.choice(CATALOG)[1]
            artist_tracks = [i for i,c in enumerate(CATALOG) if c[1] == binge_artist] or list(range(len(CATALOG)))
            for _ in range(random.randint(3, 7)):
                records.append(make_entry(ts, random.choice(artist_tracks)))
                ts += timedelta(minutes=random.randint(3, 6))
        else:
            records.append(make_entry(ts, random.randint(0, len(CATALOG)-1)))

    records.sort(key=lambda x: x["time"])
    return records[:n]


if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)
    data = generate(2200)
    path = "data/raw/watch-history.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Generated {len(data):,} YT Music records → {path}")
