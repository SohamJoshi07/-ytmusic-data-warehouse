"""
run_pipeline.py — YT Music DWH · Full Pipeline
Usage:
    python run_pipeline.py          # sample data
    python run_pipeline.py --real   # real Google Takeout data
"""
import subprocess, sys, os

def run(cmd, cwd="."):
    print(f"\n$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd)
    if r.returncode != 0:
        print(f"❌ Failed: {cmd}"); sys.exit(r.returncode)

def main():
    real = "--real" in sys.argv
    print("🎵 YT Music DWH — Full Pipeline"); print("="*40)

    if not real:
        print("\n[1/5] Generating sample data...")
        run("python scripts/generate_sample_data.py")
    else:
        print("\n[1/5] Using real Google Takeout data from data/raw/")

    print("\n[2/5] Ingesting JSON → DuckDB...")
    run("python ingestion/load_to_duckdb.py")

    print("\n[3/5] Running dbt transformations...")
    run("dbt run --profiles-dir .", cwd="dbt_ytmusic")

    print("\n[4/5] Running dbt data quality tests...")
    run("dbt test --profiles-dir .", cwd="dbt_ytmusic")

    print("\n[5/5] Loading finance data...")
    run("python load_yt_finance.py")

    print("\n→ Generating listening dashboard...")
    run("python generate_dashboard.py")

    print("\n→ Generating finance dashboard...")
    run("python generate_finance_dashboard.py")

    print("\n" + "="*40)
    print("🎉 Pipeline complete!")
    print("   dashboard/ytmusic_dashboard.html")
    print("   dashboard/yt_finance_dashboard.html\n")

if __name__ == "__main__":
    main()
