"""
yt_finance_data.py — YouTube/Alphabet financials + YT Music royalty engine
Sources: Alphabet SEC filings, MRC Data, Music industry studies 2024
"""

ALPHABET_QUARTERLY = [
    (2022,"Q1",6869,80,68011,20094),(2022,"Q2",7340,85,69685,19450),
    (2022,"Q3",7071,88,69092,17135),(2022,"Q4",7963,90,76048,18060),
    (2023,"Q1",6693,95,69787,21343),(2023,"Q2",7665,100,74600,21838),
    (2023,"Q3",7952,100,76693,21343),(2023,"Q4",9200,100,86310,23700),
    (2024,"Q1",8090,105,80539,25472),(2024,"Q2",8663,110,84742,27425),
    (2024,"Q3",8921,115,88268,28521),(2024,"Q4",9700,120,96469,30972),
]

GOOGL_PRICE_HISTORY = [
    ("2022-01",135.5),("2022-02",132.0),("2022-03",138.0),
    ("2022-04",114.0),("2022-05",110.0),("2022-06",98.0),
    ("2022-07",115.0),("2022-08",121.0),("2022-09",100.0),
    ("2022-10",100.0),("2022-11",95.0),("2022-12",88.0),
    ("2023-01",103.0),("2023-02",107.0),("2023-03",104.0),
    ("2023-04",108.0),("2023-05",125.0),("2023-06",129.0),
    ("2023-07",131.0),("2023-08",133.0),("2023-09",130.0),
    ("2023-10",140.0),("2023-11",139.0),("2023-12",141.0),
    ("2024-01",153.0),("2024-02",161.0),("2024-03",172.0),
    ("2024-04",170.0),("2024-05",176.0),("2024-06",185.0),
    ("2024-07",178.0),("2024-08",170.0),("2024-09",165.0),
    ("2024-10",180.0),("2024-11",192.0),("2024-12",196.0),
]

ROYALTY_RATES = {
    "low":0.001,"mid":0.0015,"high":0.002,"default":0.0015
}

ARTIST_TIER = {
    "Taylor Swift":"high","The Weeknd":"high","Billie Eilish":"high",
    "Harry Styles":"high","Dua Lipa":"high","Olivia Rodrigo":"high",
    "Kendrick Lamar":"high","Justin Bieber":"high","Rihanna":"high",
    "Miley Cyrus":"high","Lizzo":"mid","Lil Nas X":"mid",
    "The Kid LAROI":"mid","Glass Animals":"mid","Sam Smith":"mid",
    "Kate Bush":"mid","JVKE":"low","RAYE":"low","Rema":"low",
    "Metro Boomin":"mid","Kid Cudi":"mid","J. Cole":"mid",
}

ARTIST_GLOBAL_STREAMS_B = {
    "Taylor Swift":45.0,"The Weeknd":40.0,"Billie Eilish":28.0,
    "Harry Styles":22.0,"Dua Lipa":25.0,"Olivia Rodrigo":20.0,
    "Kendrick Lamar":30.0,"Justin Bieber":38.0,"Rihanna":35.0,
    "Miley Cyrus":20.0,"Lizzo":8.0,"Lil Nas X":12.0,
    "The Kid LAROI":8.0,"Glass Animals":5.0,"Sam Smith":12.0,
    "Kate Bush":8.0,"JVKE":3.0,"RAYE":2.0,"Rema":4.0,
    "Metro Boomin":6.0,"Kid Cudi":9.0,"J. Cole":14.0,
}

PLATFORM_BENCHMARKS = [
    ("Tidal",        0.010,0.013,"Highest payout — premium niche platform"),
    ("Apple Music",  0.007,0.010,"Higher rate, smaller 100M user base"),
    ("Amazon Music", 0.004,0.006,"Mid-tier, bundled with Prime"),
    ("Spotify",      0.003,0.005,"675M MAU — scale leader"),
    ("Deezer",       0.003,0.005,"Europe-focused streaming"),
    ("YouTube Music",0.001,0.002,"Ad-supported — lowest rate, 2B+ monthly users"),
]

def get_rate(artist):
    return ROYALTY_RATES.get(ARTIST_TIER.get(artist,"default"), 0.0015)

def estimate_from_user(artist, plays, avg_watch_pct):
    rate = get_rate(artist)
    eff  = rate * (avg_watch_pct / 100.0)
    gross = plays * eff
    return {"gross_usd":round(gross,5),"label_usd":round(gross*.75,5),
            "artist_usd":round(gross*.25,5),"rate":rate,"eff_rate":round(eff,6)}

def estimate_global(artist):
    b = ARTIST_GLOBAL_STREAMS_B.get(artist)
    if not b: return None
    rate  = get_rate(artist)
    gross = b * 1e9 * rate
    return {"global_b":b,"global_gross_m":round(gross/1e6,1),
            "global_artist_m":round(gross*.25/1e6,1)}
