"""load_yt_finance.py — Loads YouTube/Alphabet financials into DuckDB"""
import duckdb, pandas as pd, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yt_finance_data import *

DB_PATH = "data/ytmusic.duckdb"

def load_quarterly(con):
    rows = []
    for (y,q,yt_ad,yt_subs,total_rev,op_inc) in ALPHABET_QUARTERLY:
        rows.append({"year_quarter":f"{y}-{q}","year":y,"quarter":q,"quarter_num":int(q[1]),
            "yt_ad_revenue_m":yt_ad,"yt_premium_subs_m":yt_subs,"alphabet_revenue_m":total_rev,
            "operating_income_m":op_inc,"yt_revenue_share_pct":round(yt_ad/total_rev*100,1),
            "op_margin_pct":round(op_inc/total_rev*100,1)})
    df = pd.DataFrame(rows).sort_values("year_quarter")
    df["yoy_yt_growth_pct"] = df.groupby("quarter")["yt_ad_revenue_m"].pct_change().mul(100).round(1)
    con.execute("CREATE SCHEMA IF NOT EXISTS finance")
    con.execute("DROP TABLE IF EXISTS finance.yt_quarterly")
    con.execute("CREATE TABLE finance.yt_quarterly AS SELECT * FROM df")
    print(f"  OK {len(df)} quarters")

def load_stock(con):
    rows = [{"year_month":ym,"close_price":p} for ym,p in GOOGL_PRICE_HISTORY]
    df = pd.DataFrame(rows)
    df["year"]  = df["year_month"].str[:4].astype(int)
    df["month"] = df["year_month"].str[5:7].astype(int)
    df["price_change_pct"] = df["close_price"].pct_change().mul(100).round(2)
    df["all_time_high"]    = df["close_price"].cummax()
    df["drawdown_pct"]     = ((df["close_price"]-df["all_time_high"])/df["all_time_high"]*100).round(1)
    con.execute("DROP TABLE IF EXISTS finance.googl_price_history")
    con.execute("CREATE TABLE finance.googl_price_history AS SELECT * FROM df")
    print(f"  OK {len(df)} months")

def load_artist_revenue(con):
    rows_db = con.execute("""SELECT channel_name,total_plays,total_minutes,total_hours,
        avg_watch_pct,skip_rate_pct FROM main_marts.mart_channel_summary ORDER BY total_plays DESC""").fetchall()
    rows = []
    for (ch,plays,mins,hrs,wpct,skip_pct) in rows_db:
        rev  = estimate_from_user(ch,plays,wpct or 75)
        glob = estimate_global(ch)
        rows.append({"channel_name":ch,"your_play_count":int(plays),"your_watch_minutes":round(float(mins),1),
            "avg_watch_pct":round(float(wpct or 0),1),"royalty_rate_usd":rev["rate"],
            "effective_rate_usd":rev["eff_rate"],"gross_you_generated_usd":rev["gross_usd"],
            "label_kept_usd":rev["label_usd"],"artist_earned_from_you_usd":rev["artist_usd"],
            "plays_to_earn_1_dollar":round(1/rev["eff_rate"]) if rev["eff_rate"]>0 else 0,
            "global_streams_billions":glob["global_b"] if glob else None,
            "global_gross_payout_m_usd":glob["global_gross_m"] if glob else None,
            "global_artist_earned_m_usd":glob["global_artist_m"] if glob else None})
    df = pd.DataFrame(rows)
    con.execute("DROP TABLE IF EXISTS finance.artist_revenue")
    con.execute("CREATE TABLE finance.artist_revenue AS SELECT * FROM df")
    print(f"  OK {len(df)} artists")

def load_benchmarks(con):
    df = pd.DataFrame(PLATFORM_BENCHMARKS,columns=["platform","rate_min","rate_max","notes"])
    df["rate_mid"] = ((df["rate_min"]+df["rate_max"])/2).round(4)
    con.execute("DROP TABLE IF EXISTS finance.platform_benchmarks")
    con.execute("CREATE TABLE finance.platform_benchmarks AS SELECT * FROM df")
    print(f"  OK {len(df)} platforms")

if __name__ == "__main__":
    print("Loading YT Music finance data...")
    con = duckdb.connect(DB_PATH)
    load_quarterly(con); load_stock(con); load_artist_revenue(con); load_benchmarks(con)
    con.close()
    print("Done!")
