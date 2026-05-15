# 🎵 YouTube Music Data Warehouse

> An end-to-end data engineering portfolio project — from raw Google Takeout JSON to a production-grade star schema data warehouse with behavioural analytics and financial intelligence, powered by **DuckDB**, **dbt**, and **Python**.

<br>

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![DuckDB](https://img.shields.io/badge/DuckDB-0.10%2B-FFF000?style=flat&logo=duckdb&logoColor=black)](https://duckdb.org)
[![dbt](https://img.shields.io/badge/dbt--core-1.7%2B-FF694B?style=flat&logo=dbt&logoColor=white)](https://getdbt.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)
[![Tests](https://img.shields.io/badge/dbt%20Tests-20%20passing-brightgreen?style=flat)](dbt_ytmusic/models)

---

## 📌 Overview

This project transforms raw YouTube Music watch history — exported from Google Takeout — into a fully modelled analytical data warehouse. It combines personal listening behaviour analytics with YouTube's public financial data to answer two questions simultaneously:

- **Personal:** *When, what, and how deeply do you listen? Which artists do you actually engage with vs skip?*
- **Business:** *How does YouTube monetise music streaming? What does your listening contribute to artist royalties?*

The result is two live-connected dashboards generated directly from the DuckDB warehouse.

---

## 🏗️ Architecture

```
Google Takeout (watch-history.json)
            ↓
   Python Ingestion Layer
   (JSON parsing · Pandas normalisation · schema-on-read)
            ↓
   DuckDB — Raw Schema (raw.yt_history)
            ↓
   dbt Staging Layer
   (stg_yt_history — cleaning · typing · proxy variable engineering)
            ↓
   dbt Marts — Star Schema
   ┌─────────────────────────────────────────┐
   │  dim_channels   dim_videos   dim_time   │
   │           ↘         ↓        ↙          │
   │              fact_watches               │
   │           ↗         ↑        ↖          │
   │  mart_channel_summary                   │
   │  mart_monthly_trends                    │
   │  mart_listening_patterns                │
   └─────────────────────────────────────────┘
            ↓
   Finance Schema (DuckDB)
   (Alphabet SEC filings · artist royalty model · platform benchmarks)
            ↓
   Python Dashboard Generator
   (queries DuckDB at runtime → live HTML dashboards)
```

---

## ⭐ Star Schema Design

| Table | Type | Description |
|---|---|---|
| `raw.yt_history` | Raw | Direct load from Google Takeout JSON |
| `stg_yt_history` | Staging View | Cleaned, typed, skip-rate inferred |
| `dim_channels` | Dimension | One row per unique artist/channel |
| `dim_videos` | Dimension | One row per unique video |
| `dim_time` | Dimension | Rich calendar attributes (hour, day, week, quarter) |
| `fact_watches` | Fact | One row per watch event — central fact table |
| `mart_channel_summary` | Mart | Pre-aggregated artist-level analytics |
| `mart_monthly_trends` | Mart | Month-over-month listening trends |
| `mart_listening_patterns` | Mart | Hour × Day heatmap data |
| `finance.yt_quarterly` | Finance | Alphabet quarterly earnings (2022–2024) |
| `finance.artist_revenue` | Finance | Per-artist royalty estimates |
| `finance.platform_benchmarks` | Finance | Cross-platform royalty rate comparison |

---

## 📊 What This Project Analyses

### Listening Behaviour Dashboard
- **Top channels** by total hours and watch-completion rate
- **7×24 heatmap** — when exactly you listen (hour of day × day of week)
- **Skip-rate inference** — derived as a proxy variable from watch % < 45%
- **Genre distribution** across your listening history
- **Device split** — mobile vs desktop vs TV
- **Monthly trends** — stream count and hours over time

### Finance Intelligence Dashboard
- **YouTube ad revenue** — $6.9B → $9.7B quarterly growth (2022–2024)
- **Alphabet operating margin** expansion — 23.7% → 32.1%
- **GOOGL stock price** history — +123% from Dec 2022 low
- **Artist royalty estimator** — how much each artist earned from your plays
- **Platform royalty benchmarks** — Spotify vs Apple Music vs Tidal vs YouTube Music
- **Global career earnings** extrapolation for 22 tracked artists

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Windows / macOS / Linux
- Git

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/ytmusic-data-warehouse.git
cd ytmusic-data-warehouse
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the full pipeline (sample data)
```bash
python run_pipeline.py
```

This single command runs all 6 steps automatically:
1. Generates 2,200 realistic sample watch events
2. Ingests JSON → DuckDB raw schema
3. Runs all 8 dbt transformation models
4. Executes 20 data quality tests
5. Loads Alphabet financial data + artist revenue model
6. Generates both HTML dashboards

### 4. Open your dashboards
```
dashboard/ytmusic_dashboard.html       ← Listening behaviour
dashboard/yt_finance_dashboard.html    ← Finance intelligence
```
Open either file in any browser — no server needed.

---

## 📁 Project Structure

```
ytmusic-data-warehouse/
│
├── data/
│   └── raw/                          # Google Takeout files go here (gitignored)
│
├── ingestion/
│   └── load_to_duckdb.py             # JSON → DuckDB ingestion script
│
├── dbt_ytmusic/                      # dbt project
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_yt_history.sql    # Cleaning + proxy variable engineering
│   │   │   └── schema.yml            # Source definitions + staging tests
│   │   └── marts/
│   │       ├── dim_channels.sql
│   │       ├── dim_videos.sql
│   │       ├── dim_time.sql
│   │       ├── fact_watches.sql      # Central fact table
│   │       ├── mart_channel_summary.sql
│   │       ├── mart_monthly_trends.sql
│   │       ├── mart_listening_patterns.sql
│   │       └── schema.yml            # Mart tests
│   ├── dbt_project.yml
│   └── profiles.yml                  # DuckDB connection config
│
├── scripts/
│   └── generate_sample_data.py       # Generates 2,200 realistic watch events
│
├── dashboard/
│   ├── ytmusic_dashboard.html        # Auto-generated listening dashboard
│   └── yt_finance_dashboard.html     # Auto-generated finance dashboard
│
├── yt_finance_data.py                # Alphabet financials + royalty rate module
├── load_yt_finance.py                # Loads finance schema into DuckDB
├── generate_dashboard.py             # Listening dashboard generator
├── generate_finance_dashboard.py     # Finance dashboard generator
├── run_pipeline.py                   # One-command full pipeline runner
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🔌 Using Your Real YouTube Music Data

Your personal data is never committed to this repo — the `.gitignore` protects all raw files and the DuckDB database. To use your real listening history:

**Step 1** — Go to [takeout.google.com](https://takeout.google.com)

**Step 2** — Deselect all → select **YouTube and YouTube Music** only

**Step 3** — Under options → select **JSON format**

**Step 4** — Download, unzip, copy `watch-history.json` into `data/raw/`

**Step 5** — Run with real data flag:
```bash
python run_pipeline.py --real
```

Every chart instantly rebuilds with your actual personal listening history.

---

## 🧪 Data Quality

20 dbt tests run automatically on every pipeline execution:

```
✓ stg_yt_history.watch_id        — unique, not_null
✓ stg_yt_history.watched_at      — not_null
✓ stg_yt_history.video_title     — not_null
✓ stg_yt_history.channel_name    — not_null
✓ dim_channels.channel_id        — unique, not_null
✓ dim_videos.video_id_dim        — unique, not_null
✓ dim_time.time_id               — unique, not_null
✓ fact_watches.watch_id          — unique, not_null
✓ mart_channel_summary.channel_name — unique, not_null
✓ mart_monthly_trends.year_month — unique, not_null

Result: PASS=20  WARN=0  ERROR=0
```

---

## 💡 Key Technical Decisions

**Why DuckDB over PostgreSQL?**
DuckDB is columnar — optimised for analytical aggregations (`SUM`, `GROUP BY`, `AVG`) across millions of rows. PostgreSQL is row-oriented and designed for transactional workloads. For an analytics warehouse with zero concurrency requirements, DuckDB runs faster with zero setup overhead.

**Why dbt over plain SQL scripts?**
dbt enforces a layered architecture (raw → staging → marts), handles execution order automatically, generates documentation, and includes a built-in testing framework. Plain SQL scripts have none of these — they become unmaintainable at scale.

**Why infer skip rate from watch percentage?**
Unlike Spotify, YouTube Music's Takeout export has no explicit skip flag. A watch completion below 45% is a statistically reasonable proxy for intentional skipping — the user heard enough to decide they didn't want the track. This is feature engineering applied to a real-world data gap.

**Why a star schema over a flat table?**
A flat table embeds redundant string values (channel name, genre) in every fact row. The star schema stores them once in dimension tables and references them by key — reducing storage, improving query performance, and enabling clean `JOIN`-based slicing.

---

## 🛠️ Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| Language | Python 3.10+ | Ingestion, orchestration, dashboard generation |
| Warehouse | DuckDB 0.10+ | Local OLAP analytical database |
| Transform | dbt-core + dbt-duckdb | SQL modelling, testing, data lineage |
| Processing | Pandas | Data normalisation and type inference |
| Visualisation | HTML + SVG + JavaScript | Live dashboard rendering |
| Finance Data | Alphabet SEC 10-Q/10-K | Quarterly earnings (2022–2024) |

---

## 📈 Sample Insights

Running on sample data (2,182 watch events, 96.6 hours):

- **Peak listening window:** 7–11 PM on weekdays
- **Most engaged genre:** Pop (highest avg watch completion %)
- **Skip rate:** 13.2% of plays — inferred from watch % < 45%
- **Artist with highest engagement:** Full listen rate > 85%
- **YouTube ad revenue growth:** +41% from Q1 2022 to Q4 2024
- **Artist royalty rate on YouTube Music:** $0.001–$0.002 per play vs $0.003–$0.005 on Spotify

---

## 🔮 Planned Enhancements

- [ ] **Apache Airflow** — scheduled daily pipeline runs with failure alerts
- [ ] **Incremental dbt models** — process only new records each run
- [ ] **YouTube Data API enrichment** — pull video duration, view counts, category
- [ ] **Sentiment analysis** — NLP on video titles to detect mood trends
- [ ] **BigQuery migration** — cloud warehouse for production-scale data
- [ ] **Evidence.dev dashboard** — public shareable live dashboard

---

## 📄 Resume Bullets

```
• Engineered an end-to-end ELT pipeline ingesting 2,182 YouTube Music events from
  Google Takeout JSON into a DuckDB analytical warehouse, transforming raw data through
  8 dbt-core models across staging and mart layers using Kimball dimensional modelling.

• Implemented 20 automated dbt data quality tests enforcing primary key uniqueness,
  null constraints, and referential integrity, while deriving skip-rate inference as a
  proxy variable from watch-completion percentage across a 7×24 behavioural heatmap.

• Constructed a financial modelling layer integrating 12 quarters of Alphabet Inc. SEC
  earnings data with a per-stream royalty estimation model, calculating effective artist
  revenue across 22 channels adjusted for watch-completion and label revenue-share splits.

• Delivered two live Python-generated dashboards querying DuckDB at runtime, rendering
  animated SVG visualisations of listening behaviour patterns and YouTube ad revenue
  growth from $6.9B to $9.7B quarterly.
```

---

## 📜 Data Sources & Disclaimer

| Source | Usage |
|---|---|
| Google Takeout | Personal YouTube Music watch history (never committed to repo) |
| Alphabet Inc. SEC Filings | Quarterly earnings data (public record) |
| IFPI Global Music Report 2024 | Industry royalty rate benchmarks |
| MRC Data / MusicWatch | YouTube Premium subscriber estimates |

> **Privacy:** No personal data is committed to this repository. The `.gitignore` excludes all files in `data/raw/` and the compiled `data/*.duckdb` database. Only code, SQL models, and configuration are version-controlled.

> **Disclaimer:** Artist revenue figures are estimates based on publicly reported royalty rates and stream counts. Actual payouts vary by contract, territory, and account type.

---

## 📬 Contact

Built as a data engineering portfolio project.
Feel free to fork, star ⭐, or open an issue with questions.

---

*YouTube Music Data Warehouse · DuckDB + dbt + Python · Data Engineering Portfolio*
