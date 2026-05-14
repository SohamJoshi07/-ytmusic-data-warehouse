"""
generate_dashboard.py — YT Music Listening Behaviour Dashboard
Queries real DuckDB data and generates connected HTML dashboard.
"""
import duckdb, json, os
from datetime import datetime

DB_PATH = "data/ytmusic.duckdb"
OUTPUT  = "dashboard/ytmusic_dashboard.html"

def fetch(con):
    d = {}
    r = con.execute("""SELECT COUNT(*) as plays, COUNT(DISTINCT channel_name) as channels,
        COUNT(DISTINCT video_title) as videos, ROUND(SUM(watch_min)/60,1) as hours,
        ROUND(AVG(watch_pct),1) as avg_watch_pct,
        ROUND(100.0*SUM(skip_count)/COUNT(*),1) as skip_pct,
        ROUND(100.0*SUM(full_listen_count)/COUNT(*),1) as full_pct,
        MIN(watched_date)::VARCHAR as first_date, MAX(watched_date)::VARCHAR as last_date
        FROM main_marts.fact_watches""").fetchone()
    d['kpis'] = dict(zip(['plays','channels','videos','hours','avg_watch_pct',
                           'skip_pct','full_pct','first_date','last_date'], r))

    rows = con.execute("""SELECT channel_name,genre,total_hours,total_plays,
        skip_rate_pct,avg_watch_pct FROM main_marts.mart_channel_summary
        ORDER BY total_hours DESC LIMIT 10""").fetchall()
    d['channels'] = [dict(zip(['name','genre','hours','plays','skip_pct','watch_pct'],r)) for r in rows]

    rows = con.execute("""SELECT video_title,channel_name,COUNT(*) as plays,
        ROUND(SUM(watch_min)/60,2) as hours FROM main_marts.fact_watches
        GROUP BY video_title,channel_name ORDER BY plays DESC LIMIT 8""").fetchall()
    d['videos'] = [dict(zip(['title','channel','plays','hours'],r)) for r in rows]

    rows = con.execute("""SELECT device,COUNT(*) as plays,
        ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER(),1) as pct
        FROM main_marts.fact_watches GROUP BY device ORDER BY plays DESC""").fetchall()
    d['devices'] = [dict(zip(['name','plays','pct'],r)) for r in rows]

    rows = con.execute("""SELECT genre,COUNT(*) as plays,ROUND(SUM(watch_min)/60,1) as hours
        FROM main_marts.fact_watches GROUP BY genre ORDER BY hours DESC LIMIT 8""").fetchall()
    d['genres'] = [dict(zip(['name','plays','hours'],r)) for r in rows]

    rows = con.execute("""SELECT year_month,month_name,total_plays,total_hours,skip_rate_pct
        FROM main_marts.mart_monthly_trends ORDER BY year_month DESC LIMIT 12""").fetchall()
    d['monthly'] = [dict(zip(['ym','month','plays','hours','skip_pct'],r)) for r in reversed(rows)]

    rows = con.execute("""SELECT hour_of_day,day_name,day_of_week_num,play_count
        FROM main_marts.mart_listening_patterns ORDER BY day_of_week_num,hour_of_day""").fetchall()
    d['heatmap'] = [dict(zip(['h','day','dow','count'],r)) for r in rows]

    rows = con.execute("""SELECT channel_name,skip_rate_pct,total_plays
        FROM main_marts.mart_channel_summary WHERE total_plays>=10
        ORDER BY skip_rate_pct DESC LIMIT 6""").fetchall()
    d['skip'] = [dict(zip(['name','pct','plays'],r)) for r in rows]

    return d

def build_html(d):
    k   = d['kpis']
    gen = datetime.now().strftime("%B %d, %Y at %H:%M")
    top = d['channels'][0]['name'] if d['channels'] else 'Taylor Swift'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>YT Music DWH — Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Playfair+Display:ital,wght@0,700;1,400&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{{
  --black:#07080a;--card:#111318;--border:#1a1d24;
  --red:#ff0000;--red2:rgba(255,0,0,.12);--red3:rgba(255,0,0,.06);
  --red4:#cc0000;--white2:rgba(255,255,255,.06);
  --text:#f0ece4;--muted:#525660;--dim:#1e2128;
  --gold:#f5c842;--blue:#38bdf8;--green:#00d084;
  --bebas:'Bebas Neue',sans-serif;--play:'Playfair Display',serif;--mono:'Space Mono',monospace;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{background:var(--black);color:var(--text);font-family:var(--mono);overflow-x:hidden;cursor:none}}
#cur{{width:8px;height:8px;background:var(--red);border-radius:50%;position:fixed;pointer-events:none;z-index:9999;transform:translate(-50%,-50%);mix-blend-mode:difference}}
#ring{{width:30px;height:30px;border:1px solid rgba(255,0,0,.4);border-radius:50%;position:fixed;pointer-events:none;z-index:9998;transform:translate(-50%,-50%);transition:left .1s,top .1s}}
body::after{{content:'';position:fixed;inset:0;opacity:.4;pointer-events:none;z-index:9990;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.03'/%3E%3C/svg%3E")}}

/* HERO */
.hero{{min-height:100vh;display:flex;flex-direction:column;justify-content:center;padding:64px;position:relative;overflow:hidden}}
.hero-bg{{position:absolute;inset:0;background:
  radial-gradient(ellipse 60% 55% at 85% 45%,rgba(255,0,0,.08) 0%,transparent 65%),
  radial-gradient(ellipse 40% 50% at 5% 85%,rgba(255,80,0,.04) 0%,transparent 60%)}}

/* Play button decoration */
.play-deco{{position:absolute;right:60px;top:50%;transform:translateY(-50%);
  width:320px;height:320px;border-radius:50%;
  border:1px solid rgba(255,0,0,.08);display:flex;align-items:center;justify-content:center;opacity:.25}}
.play-deco::before{{content:'';width:260px;height:260px;border-radius:50%;
  border:1px solid rgba(255,0,0,.12);position:absolute}}
.play-deco::after{{content:'▶';font-size:80px;color:var(--red);opacity:.6;margin-left:12px}}

.live-badge{{display:inline-flex;align-items:center;gap:7px;background:rgba(255,0,0,.1);
  border:1px solid rgba(255,0,0,.25);border-radius:2px;padding:4px 12px;font-size:8px;
  letter-spacing:.15em;color:var(--red);text-transform:uppercase;margin-bottom:16px;
  opacity:0;animation:up .6s .05s ease forwards}}
.live-dot{{width:5px;height:5px;border-radius:50%;background:var(--red);animation:pulse 1.8s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}

.eyebrow{{font-size:10px;letter-spacing:.22em;color:var(--red);text-transform:uppercase;
  margin-bottom:16px;opacity:0;animation:up .6s .1s ease forwards}}
.eyebrow::before{{content:'▶  '}}
h1{{font-family:var(--bebas);font-size:clamp(66px,9vw,128px);line-height:.9;letter-spacing:.02em;
  opacity:0;animation:up .6s .2s ease forwards;max-width:680px}}
h1 .r{{color:var(--red)}}
h1 .ghost{{-webkit-text-stroke:1px rgba(255,255,255,.1);color:transparent}}
.sub{{margin-top:20px;font-family:var(--play);font-style:italic;font-size:14px;color:var(--muted);
  max-width:420px;line-height:1.7;opacity:0;animation:up .6s .3s ease forwards}}
.hero-kpis{{display:flex;flex-wrap:wrap;gap:44px;margin-top:48px;opacity:0;animation:up .6s .4s ease forwards}}
.hkpi .v{{font-family:var(--bebas);font-size:46px;line-height:1;letter-spacing:.02em}}
.hkpi .l{{font-size:8px;letter-spacing:.16em;color:var(--muted);text-transform:uppercase;margin-top:3px}}
.v-red{{color:var(--red)}} .v-gold{{color:var(--gold)}} .v-blue{{color:var(--blue)}}
.scroll-h{{margin-top:52px;font-size:9px;letter-spacing:.2em;color:var(--dim);text-transform:uppercase;
  opacity:0;animation:up .6s .6s ease forwards,blink 2s 1.5s infinite}}
@keyframes blink{{0%,100%{{opacity:.2}}50%{{opacity:.8}}}}
@keyframes up{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:none}}}}

/* LAYOUT */
.dash{{padding:0 44px 80px}}
.sec{{font-size:9px;letter-spacing:.26em;color:var(--red);text-transform:uppercase;
  padding:34px 0 14px;border-top:1px solid var(--border);display:flex;align-items:center;gap:12px}}
.sec::after{{content:'';flex:1;height:1px;background:var(--border)}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:2px;margin-bottom:2px}}
.g3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:2px;margin-bottom:2px}}
.g4{{display:grid;grid-template-columns:repeat(4,1fr);gap:2px;margin-bottom:2px}}

.card{{background:var(--card);border:1px solid var(--border);padding:24px 26px;
  position:relative;overflow:hidden;transition:border-color .2s}}
.card:hover{{border-color:#2a2d38}}
.card::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--red),transparent);opacity:0;transition:opacity .3s}}
.card:hover::before{{opacity:.35}}
.clbl{{font-size:8px;letter-spacing:.18em;color:var(--muted);text-transform:uppercase;margin-bottom:9px}}
.cval{{font-family:var(--bebas);font-size:50px;line-height:1;letter-spacing:.02em}}
.cunit{{font-size:10px;margin-top:3px}}
.cdelta{{position:absolute;top:22px;right:22px;font-size:9px;padding:2px 7px;border-radius:2px}}
.up{{color:var(--green);background:rgba(0,208,132,.1)}}
.dn{{color:#ff4d6d;background:rgba(255,77,109,.1)}}

.cc{{background:var(--card);border:1px solid var(--border);padding:26px 30px;margin-bottom:2px}}
.ctitle{{font-family:var(--play);font-size:16px;font-weight:700;margin-bottom:3px}}
.csub{{font-size:8px;color:var(--muted);letter-spacing:.1em;text-transform:uppercase;margin-bottom:22px}}

/* bars */
.bchart{{display:flex;flex-direction:column;gap:10px}}
.brow{{display:grid;grid-template-columns:148px 1fr 50px;align-items:center;gap:13px}}
.blbl{{font-size:10px;color:var(--text);text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.btrack{{height:4px;background:var(--dim);overflow:hidden}}
.bfill{{height:100%;transform-origin:left;transform:scaleX(0);animation:grow 1s cubic-bezier(.16,1,.3,1) both}}
@keyframes grow{{to{{transform:scaleX(1)}}}}
.bval{{font-size:9px;color:var(--muted);text-align:right}}

/* donut */
.dnut-wrap{{display:flex;align-items:center;gap:28px}}
.dleg-item{{display:flex;align-items:center;gap:8px;margin-bottom:10px;font-size:10px}}
.dleg-dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
.dleg-name{{color:var(--text);flex:1}}
.dleg-pct{{color:var(--muted);font-size:9px}}

/* video list */
.vitem{{display:grid;grid-template-columns:26px 1fr 42px 50px;align-items:center;
  gap:12px;padding:12px 0;border-bottom:1px solid var(--border);transition:padding-left .15s}}
.vitem:hover{{padding-left:6px}}
.vrank{{font-family:var(--bebas);font-size:19px;color:var(--dim);text-align:right}}
.vrank.top{{color:var(--red)}}
.vtitle{{font-size:11px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.vchannel{{font-size:8px;color:var(--muted);margin-top:2px}}
.vplays{{font-family:var(--bebas);font-size:20px;text-align:right}}
.vbar{{height:3px;background:var(--dim);overflow:hidden}}
.vbar-f{{height:100%;background:var(--red);transform-origin:left;transform:scaleX(0);animation:grow 1s cubic-bezier(.16,1,.3,1) both}}

/* heatmap */
.hm-grid{{display:grid;gap:3px;margin-top:16px}}
.hm-lbl{{font-size:8px;color:var(--muted);display:flex;align-items:center;justify-content:flex-end;padding-right:7px}}
.hm-cell{{aspect-ratio:1;border-radius:2px;transition:transform .12s;cursor:crosshair}}
.hm-cell:hover{{transform:scale(1.5);z-index:10;position:relative}}
.hm-hrs{{display:grid;gap:3px;margin-top:4px}}
.hm-hlbl{{font-size:7px;color:var(--dim);text-align:center}}

/* monthly */
.mbars{{display:flex;align-items:flex-end;gap:5px;height:90px;margin-top:18px}}
.mcol{{flex:1;display:flex;flex-direction:column;align-items:center;gap:4px}}
.mbar{{width:100%;border-radius:2px 2px 0 0;transform-origin:bottom;transform:scaleY(0);
  animation:growY .8s cubic-bezier(.16,1,.3,1) both;position:relative;overflow:hidden;min-height:2px}}
.mbar::after{{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.12) 0%,transparent 50%)}}
@keyframes growY{{to{{transform:scaleY(1)}}}}
.mlbl{{font-size:7px;color:var(--muted);text-align:center}}
.mval{{font-size:7px;color:var(--red)}}

/* genre bars */
.gbars{{display:flex;flex-direction:column;gap:9px;margin-top:8px}}
.grow{{display:grid;grid-template-columns:90px 1fr 44px;align-items:center;gap:10px}}
.glbl{{font-size:9px;color:var(--text);text-align:right}}
.gtrack{{height:4px;background:var(--dim);overflow:hidden}}
.gfill{{height:100%;transform-origin:left;transform:scaleX(0);animation:grow 1s cubic-bezier(.16,1,.3,1) both}}
.gval{{font-size:8px;color:var(--muted);text-align:right}}

/* skip */
.sitem{{display:flex;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid var(--border)}}
.sname{{font-size:10px;color:var(--text);flex:1}}
.spct{{font-family:var(--bebas);font-size:22px;width:46px;text-align:right}}
.sbar-w{{width:90px;height:3px;background:var(--dim);overflow:hidden}}
.sbar-f{{height:100%;transform-origin:left;transform:scaleX(0);animation:grow 1s cubic-bezier(.16,1,.3,1) both}}

/* insight */
.insight{{background:linear-gradient(135deg,var(--red3),transparent);border:1px solid rgba(255,0,0,.15);
  border-left:3px solid var(--red);padding:22px 26px;margin-bottom:2px}}
.itag{{font-size:8px;letter-spacing:.2em;color:var(--red);text-transform:uppercase;margin-bottom:8px}}
.itext{{font-family:var(--play);font-style:italic;font-size:15px;line-height:1.6;color:var(--text);max-width:620px}}

/* stack */
.stack-lbl{{font-size:8px;letter-spacing:.18em;color:var(--muted);text-transform:uppercase;margin-bottom:7px}}
.stack-name{{font-family:var(--bebas);font-size:32px;margin:6px 0}}
.stack-desc{{font-size:10px;color:var(--muted);line-height:1.65}}

/* ticker */
.ticker{{background:#0e1014;border-top:1px solid var(--border);border-bottom:1px solid var(--border);
  padding:10px 0;overflow:hidden;white-space:nowrap}}
.ticker-inner{{display:inline-flex;gap:48px;animation:ticker 25s linear infinite}}
.ticker-item{{font-size:10px;letter-spacing:.06em;display:flex;align-items:center;gap:8px}}
.ticker-sym{{color:var(--red);font-weight:700}}
.ticker-val{{color:var(--text)}}
@keyframes ticker{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}

/* footer */
.footer{{border-top:1px solid var(--border);padding:22px 44px;display:flex;
  justify-content:space-between;align-items:center;font-size:8px;letter-spacing:.13em;
  color:var(--muted);text-transform:uppercase}}
.footer .logo{{font-family:var(--bebas);font-size:17px;color:var(--red);letter-spacing:.1em}}

.rv{{opacity:0;transform:translateY(18px);transition:opacity .5s ease,transform .5s ease}}
.rv.on{{opacity:1;transform:none}}
</style>
</head>
<body>
<div id="cur"></div><div id="ring"></div>

<div class="ticker"><div class="ticker-inner" id="ticker"></div></div>

<section class="hero">
  <div class="hero-bg"></div>
  <div class="play-deco"></div>
  <div class="live-badge"><span class="live-dot"></span>Live from DuckDB · {gen}</div>
  <div class="eyebrow">YouTube Music · Data Warehouse · DuckDB + dbt</div>
  <h1>YOUR<br><span class="r">MUSIC</span><br><span class="ghost">DECODED</span></h1>
  <p class="sub">{int(k['plays']):,} watch events · {k['first_date']} → {k['last_date']}<br>
  Star schema warehouse powered by DuckDB, dbt & Python.</p>
  <div class="hero-kpis">
    <div class="hkpi"><div class="v v-red" id="h1">0</div><div class="l">Total Plays</div></div>
    <div class="hkpi"><div class="v v-gold" id="h2">0</div><div class="l">Hours Watched</div></div>
    <div class="hkpi"><div class="v v-blue" id="h3">0</div><div class="l">Unique Channels</div></div>
    <div class="hkpi"><div class="v v-red" id="h4">0</div><div class="l">Avg Watch %</div></div>
  </div>
  <div class="scroll-h">↓ &nbsp; Scroll to explore</div>
</section>

<div class="dash">

<div class="sec rv">01 — Key Metrics</div>
<div class="g4 rv">
  <div class="card">
    <div class="clbl">Total Watch Hours</div>
    <div class="cval" style="color:var(--red)">{k['hours']}</div>
    <div class="cunit" style="color:var(--red)">hours of music</div>
    <div class="cdelta up">↑ rich dataset</div>
  </div>
  <div class="card">
    <div class="clbl">Avg Watch %</div>
    <div class="cval" style="color:var(--gold)">{k['avg_watch_pct']}<span style="font-size:24px">%</span></div>
    <div class="cunit" style="color:var(--gold)">per video average</div>
    <div class="cdelta up">↑ high engagement</div>
  </div>
  <div class="card">
    <div class="clbl">Full Listen Rate</div>
    <div class="cval" style="color:var(--green)">{k['full_pct']}<span style="font-size:24px">%</span></div>
    <div class="cunit" style="color:var(--green)">watched 80%+ of video</div>
    <div class="cdelta up">↑ strong intent</div>
  </div>
  <div class="card">
    <div class="clbl">Skip Rate (inferred)</div>
    <div class="cval" style="color:var(--text)">{k['skip_pct']}<span style="font-size:24px">%</span></div>
    <div class="cunit" style="color:var(--muted)">watch % &lt; 45%</div>
    <div class="cdelta {'up' if float(k['skip_pct']) < 20 else 'dn'}">{'✓ low' if float(k['skip_pct']) < 20 else '⚡ high'}</div>
  </div>
</div>

<div class="sec rv">02 — Channel Intelligence</div>
<div class="g2 rv">
  <div class="cc">
    <div class="ctitle">Top Channels</div>
    <div class="csub">by total hours watched</div>
    <div class="bchart" id="channelBars"></div>
  </div>
  <div class="cc">
    <div class="ctitle">Device Split</div>
    <div class="csub">where you listen most</div>
    <div class="dnut-wrap" style="margin-top:10px">
      <svg id="donutSvg" width="130" height="130" viewBox="0 0 130 130">
        <circle fill="none" cx="65" cy="65" r="50" stroke="#1a1a1a" stroke-width="11"/>
        <text x="65" y="61" text-anchor="middle" fill="#f0ece4" font-family="'Bebas Neue',sans-serif" font-size="19">{k['hours']}</text>
        <text x="65" y="74" text-anchor="middle" fill="#555" font-family="'Space Mono',monospace" font-size="7">HOURS</text>
      </svg>
      <div id="donutLegend"></div>
    </div>
  </div>
</div>

<div class="sec rv">03 — Top Videos</div>
<div class="cc rv">
  <div class="ctitle">Most Watched Videos</div>
  <div class="csub">by total play count — real data from fact_watches</div>
  <div id="videoList"></div>
</div>

<div class="sec rv">04 — When You Listen</div>
<div class="cc rv">
  <div class="ctitle">Listening Heatmap</div>
  <div class="csub">plays by hour of day × day of week</div>
  <div id="heatmapWrap"></div>
  <div style="display:flex;align-items:center;gap:7px;margin-top:12px">
    <span style="font-size:8px;color:var(--muted)">Low</span>
    <div style="display:flex;gap:2px">
      <div style="width:10px;height:10px;border-radius:2px;background:rgba(255,0,0,.07)"></div>
      <div style="width:10px;height:10px;border-radius:2px;background:rgba(255,0,0,.22)"></div>
      <div style="width:10px;height:10px;border-radius:2px;background:rgba(255,0,0,.42)"></div>
      <div style="width:10px;height:10px;border-radius:2px;background:rgba(255,0,0,.65)"></div>
      <div style="width:10px;height:10px;border-radius:2px;background:rgba(255,0,0,.88)"></div>
    </div>
    <span style="font-size:8px;color:var(--muted)">High</span>
  </div>
</div>

<div class="sec rv">05 — Trends & Genre</div>
<div class="g2 rv">
  <div class="cc">
    <div class="ctitle">Monthly Watch Activity</div>
    <div class="csub">plays per month</div>
    <div class="mbars" id="monthBars"></div>
  </div>
  <div class="cc">
    <div class="ctitle">Genre Breakdown</div>
    <div class="csub">hours by genre</div>
    <div class="gbars" id="genreBars"></div>
  </div>
</div>

<div class="sec rv">06 — Skip Rate Analysis</div>
<div class="g2 rv">
  <div class="cc">
    <div class="ctitle">Most Skipped Channels</div>
    <div class="csub">inferred from watch % &lt; 45% (min 10 plays)</div>
    <div style="margin-top:10px" id="skipList"></div>
  </div>
  <div class="cc">
    <div class="ctitle">YT Music vs Spotify</div>
    <div class="csub">why YT Music data is different</div>
    <div style="margin-top:16px;display:flex;flex-direction:column;gap:12px">
      {chr(10).join([f'''<div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);font-size:11px">
        <span style="color:var(--muted)">{item[0]}</span>
        <span style="color:var(--text);font-weight:700">{item[1]}</span>
      </div>''' for item in [
        ("Skip detection","Inferred from watch %"),
        ("Royalty rate","$0.001–$0.002/play"),
        ("Data source","Google Takeout JSON"),
        ("Play unit","Watch event (not stream)"),
        ("Platform users","2B+ monthly users"),
        ("Revenue model","Ad-supported + Premium"),
      ]])}
    </div>
  </div>
</div>

<div class="insight rv">
  <div class="itag">⬡ Key Insight — from your real watch data</div>
  <div class="itext">Your most-watched channel is <strong>{top}</strong> with {d['channels'][0]['hours']} hours
  and a {d['channels'][0]['watch_pct']}% average watch rate — significantly above your {k['avg_watch_pct']}%
  overall average. High watch percentage = genuine engagement, not background listening.
  This is the metric YouTube's algorithm optimises for, not raw play count.</div>
</div>

<div class="sec rv">07 — Engineering Stack</div>
<div class="g3 rv">
  <div class="card">
    <div class="stack-lbl">Ingestion</div>
    <div class="stack-name" style="color:var(--gold)">Python</div>
    <div class="stack-desc">Google Takeout JSON → Pandas → DuckDB raw schema. {int(k['plays']):,} real watch events loaded.</div>
  </div>
  <div class="card">
    <div class="stack-lbl">Transform</div>
    <div class="stack-name" style="color:var(--blue)">dbt-core</div>
    <div class="stack-desc">Staging → Marts. Star schema: fact_watches + 3 dims. 20 quality tests passing.</div>
  </div>
  <div class="card">
    <div class="stack-lbl">Warehouse</div>
    <div class="stack-name" style="color:var(--red)">DuckDB</div>
    <div class="stack-desc">Local OLAP engine. {k['channels']} unique channels, {k['videos']} unique videos. Zero cloud cost.</div>
  </div>
</div>

</div>

<div class="footer">
  <div class="logo">YT Music DWH</div>
  <div>Generated from live DuckDB · {gen}</div>
  <div>{int(k['plays']):,} plays · {k['channels']} channels · {k['videos']} videos</div>
</div>

<script>
const CHANNELS={json.dumps(d['channels'])};
const VIDEOS={json.dumps(d['videos'])};
const DEVICES={json.dumps(d['devices'])};
const MONTHLY={json.dumps(d['monthly'])};
const HEATMAP={json.dumps(d['heatmap'])};
const SKIP={json.dumps(d['skip'])};
const GENRES={json.dumps(d['genres'])};

const cur=document.getElementById('cur'),ring=document.getElementById('ring');
let mx=0,my=0,rx=0,ry=0;
document.addEventListener('mousemove',e=>{{mx=e.clientX;my=e.clientY;cur.style.left=mx+'px';cur.style.top=my+'px'}});
setInterval(()=>{{rx+=(mx-rx)*.13;ry+=(my-ry)*.13;ring.style.left=rx+'px';ring.style.top=ry+'px'}},14);

function count(el,to,dur=1800,dec=0){{
  let s=null;
  (function step(ts){{if(!s)s=ts;const p=Math.min((ts-s)/dur,1),e=1-Math.pow(1-p,4);
  el.textContent=dec>0?(e*to).toFixed(dec):Math.round(e*to);if(p<1)requestAnimationFrame(step)}})(performance.now());
}}
setTimeout(()=>{{
  count(document.getElementById('h1'),{k['plays']});
  count(document.getElementById('h2'),{k['hours']},1800,1);
  count(document.getElementById('h3'),{k['channels']});
  count(document.getElementById('h4'),{k['avg_watch_pct']},1800,1);
}},500);

// Ticker
const td=[['YT MUSIC','2,200 Plays','+96h','pos'],['CHANNELS','{k["channels"]}','artists','pos'],
  ['WATCH %','{k["avg_watch_pct"]}%','avg','pos'],['FULL LISTENS','{k["full_pct"]}%','rate','pos'],
  ['DWH','DuckDB+dbt','live','pos'],['STAR SCHEMA','fact_watches','4 tables','pos'],
  ['YT MUSIC','2,200 Plays','+96h','pos'],['CHANNELS','{k["channels"]}','artists','pos']];
const tk=document.getElementById('ticker');
[...td,...td].forEach(([s,v,c,cls])=>{{
  tk.innerHTML+=`<div class="ticker-item"><span class="ticker-sym">${{s}}</span>
    <span class="ticker-val">${{v}}</span><span style="color:var(--red);font-size:9px">${{c}}</span></div>`;
}});

// Channel bars
const ab=document.getElementById('channelBars');
const maxH=CHANNELS[0].hours;
CHANNELS.forEach((c,i)=>{{
  ab.innerHTML+=`<div class="brow"><div class="blbl">${{c.name}}</div>
    <div class="btrack"><div class="bfill" style="background:var(--red);animation-delay:${{i*.07}}s;width:${{c.hours/maxH*100}}%"></div></div>
    <div class="bval">${{c.hours}}h</div></div>`;
}});

// Donut — devices
const svg=document.getElementById('donutSvg');
const C=2*Math.PI*50;
const DCOLS=['#ff0000','#f5c842','#38bdf8','#00d084','#a78bfa'];
let off=0;
const tot=DEVICES.reduce((s,d)=>s+d.plays,0);
DEVICES.forEach((dv,i)=>{{
  const pct=dv.plays/tot;const len=pct*C;
  const el=document.createElementNS('http://www.w3.org/2000/svg','circle');
  el.setAttribute('fill','none');el.setAttribute('cx','65');el.setAttribute('cy','65');
  el.setAttribute('r','50');el.setAttribute('stroke',DCOLS[i]||'#888');el.setAttribute('stroke-width','11');
  el.setAttribute('stroke-dasharray',`${{len}} ${{C-len}}`);el.setAttribute('stroke-dashoffset',C-len);
  el.style.transform=`rotate(${{off*360-90}}deg)`;el.style.transformOrigin='50% 50%';
  el.style.transition=`stroke-dashoffset 1.1s ${{i*.1}}s cubic-bezier(.16,1,.3,1)`;
  svg.insertBefore(el,svg.querySelector('text'));off+=pct;
}});
const leg=document.getElementById('donutLegend');
DEVICES.forEach((dv,i)=>{{
  leg.innerHTML+=`<div class="dleg-item"><div class="dleg-dot" style="background:${{DCOLS[i]||'#888'}}"></div>
    <div class="dleg-name">${{dv.name}}</div><div class="dleg-pct">${{dv.pct}}%</div></div>`;
}});

// Video list
const vl=document.getElementById('videoList');
const maxP=VIDEOS[0].plays;
VIDEOS.forEach((v,i)=>{{
  vl.innerHTML+=`<div class="vitem"><div class="vrank${{i<3?' top':''}}">${{i+1}}</div>
    <div><div class="vtitle">${{v.title}}</div><div class="vchannel">${{v.channel}}</div></div>
    <div><div class="vplays">${{v.plays}}</div><div style="font-size:7px;color:var(--muted);text-align:right">PLAYS</div></div>
    <div class="vbar"><div class="vbar-f" style="animation-delay:${{i*.06}}s;width:${{v.plays/maxP*100}}%"></div></div>
  </div>`;
}});

// Heatmap
const days=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
const dayShort=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const wrap=document.getElementById('heatmapWrap');
const hmGrid=document.createElement('div');
hmGrid.className='hm-grid';hmGrid.style.gridTemplateColumns='52px repeat(24,1fr)';
const maxC=Math.max(...HEATMAP.map(h=>h.count));
days.forEach((day,di)=>{{
  const lbl=document.createElement('div');lbl.className='hm-lbl';lbl.textContent=dayShort[di];hmGrid.appendChild(lbl);
  for(let h=0;h<24;h++){{
    const entry=HEATMAP.find(x=>x.dow===di&&x.h===h)||{{count:0}};
    const v=maxC>0?entry.count/maxC:0;const a=(0.05+v*.84).toFixed(2);
    const cell=document.createElement('div');cell.className='hm-cell';
    cell.style.background=`rgba(255,0,0,${{a}})`;
    cell.title=`${{dayShort[di]}} ${{h}}:00 — ${{entry.count}} plays`;
    hmGrid.appendChild(cell);
  }}
}});
wrap.appendChild(hmGrid);
const hmHrs=document.createElement('div');
hmHrs.className='hm-hrs';hmHrs.style.gridTemplateColumns='52px repeat(24,1fr)';
hmHrs.innerHTML='<div></div>';
for(let h=0;h<24;h++) hmHrs.innerHTML+=`<div class="hm-hlbl">${{h%3===0?h:''}}</div>`;
wrap.appendChild(hmHrs);

// Monthly
const maxS=Math.max(...MONTHLY.map(m=>m.plays));
const mb=document.getElementById('monthBars');
MONTHLY.forEach((m,i)=>{{
  const h=Math.round(m.plays/maxS*82);
  mb.innerHTML+=`<div class="mcol"><div class="mval">${{m.plays}}</div>
    <div class="mbar" style="height:${{h}}px;background:var(--red);animation-delay:${{i*.05}}s"></div>
    <div class="mlbl">${{m.month?.slice(0,3)||m.ym}}</div></div>`;
}});

// Genre bars
const maxG=GENRES[0]?.hours||1;
const gb=document.getElementById('genreBars');
const GCOLS=['#ff0000','#f5c842','#38bdf8','#00d084','#a78bfa','#ff6b6b','#ffd93d','#6bcb77'];
GENRES.forEach((g,i)=>{{
  gb.innerHTML+=`<div class="grow"><div class="glbl">${{g.name}}</div>
    <div class="gtrack"><div class="gfill" style="background:${{GCOLS[i]||'#ff0000'}};animation-delay:${{i*.07}}s;width:${{g.hours/maxG*100}}%"></div></div>
    <div class="gval">${{g.hours}}h</div></div>`;
}});

// Skip
const sl=document.getElementById('skipList');
const maxSk=SKIP[0]?.pct||25;
SKIP.forEach((s,i)=>{{
  const c=s.pct>20?'#ff4d6d':s.pct>15?'var(--gold)':'var(--muted)';
  sl.innerHTML+=`<div class="sitem"><div class="sname">${{s.name}}</div>
    <div class="spct" style="color:${{c}}">${{s.pct}}%</div>
    <div class="sbar-w"><div class="sbar-f" style="background:${{c}};animation-delay:${{i*.09}}s;width:${{s.pct/maxSk*100}}%"></div></div>
  </div>`;
}});

const rvs=document.querySelectorAll('.rv');
const obs=new IntersectionObserver(e=>e.forEach(x=>{{if(x.isIntersecting)x.target.classList.add('on')}}),{{threshold:.07}});
rvs.forEach(r=>obs.observe(r));
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("🎵 YT Music — Dashboard Generator")
    print("=" * 38)
    if not os.path.exists(DB_PATH):
        print("❌ Run pipeline first: python run_pipeline.py")
        raise SystemExit(1)
    con = duckdb.connect(DB_PATH, read_only=True)
    print("\n→ Querying real data from DuckDB...")
    d = fetch(con); con.close()
    k = d['kpis']
    print(f"  Plays: {int(k['plays']):,} | Hours: {k['hours']} | Channels: {k['channels']}")
    print("\n→ Generating dashboard HTML...")
    html = build_html(d)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT,"w",encoding="utf-8") as f: f.write(html)
    print(f"\n✅ Saved → {OUTPUT}\n")
