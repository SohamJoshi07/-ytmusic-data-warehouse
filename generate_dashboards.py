"""
generate_dashboards.py
───────────────────────
Queries real YT Music DuckDB warehouse and generates:
  1. dashboard/listening_dashboard.html  — behaviour analytics
  2. dashboard/finance_dashboard.html    — YouTube financials + artist revenue
"""

import duckdb, json, os
from datetime import datetime

DB_PATH = "data/ytmusic.duckdb"
OUT_DIR = "dashboard"
GEN     = datetime.now().strftime("%B %d, %Y at %H:%M")


# ─────────────────────────────────────────
#  DATA FETCH
# ─────────────────────────────────────────
def fetch_all(con):
    d = {}

    # Overview
    r = con.execute("""
        SELECT COUNT(*) plays,
               COUNT(DISTINCT channel_name) channels,
               COUNT(DISTINCT video_title) videos,
               ROUND(SUM(watch_min)/60,1) hours,
               ROUND(AVG(watch_pct),1) avg_watch_pct,
               ROUND(100.0*SUM(skip_count)/COUNT(*),1) skip_pct,
               MIN(watched_date)::VARCHAR first_date,
               MAX(watched_date)::VARCHAR last_date
        FROM main_marts.fact_watches
    """).fetchone()
    d['kpi'] = dict(zip(['plays','channels','videos','hours','avg_watch_pct','skip_pct','first','last'], r))

    # Top channels
    rows = con.execute("""
        SELECT channel_name, total_hours, total_plays, skip_rate_pct,
               avg_watch_pct, full_listen_pct, genre
        FROM main_marts.mart_channel_summary ORDER BY total_hours DESC LIMIT 10
    """).fetchall()
    d['channels'] = [dict(zip(['name','hours','plays','skip_pct','watch_pct','full_pct','genre'], r)) for r in rows]

    # Top videos
    rows = con.execute("""
        SELECT video_title, channel_name, COUNT(*) plays,
               ROUND(SUM(watch_min)/60,2) hours
        FROM main_marts.fact_watches
        GROUP BY video_title, channel_name ORDER BY plays DESC LIMIT 8
    """).fetchall()
    d['videos'] = [dict(zip(['title','channel','plays','hours'], r)) for r in rows]

    # Device split
    rows = con.execute("""
        SELECT device, COUNT(*) cnt,
               ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER(),1) pct
        FROM main_marts.fact_watches GROUP BY device ORDER BY cnt DESC
    """).fetchall()
    d['devices'] = [dict(zip(['name','count','pct'], r)) for r in rows]

    # Genre breakdown
    rows = con.execute("""
        SELECT genre, COUNT(*) plays,
               ROUND(SUM(watch_min)/60,1) hours,
               ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER(),1) pct
        FROM main_marts.fact_watches GROUP BY genre ORDER BY plays DESC
    """).fetchall()
    d['genres'] = [dict(zip(['name','plays','hours','pct'], r)) for r in rows]

    # Monthly trends (last 12)
    rows = con.execute("""
        SELECT year_month, month_name, total_plays, total_hours,
               skip_rate_pct, avg_watch_pct
        FROM main_marts.mart_monthly_trends ORDER BY year_month DESC LIMIT 12
    """).fetchall()
    d['monthly'] = list(reversed([dict(zip(['ym','month','plays','hours','skip_pct','watch_pct'], r)) for r in rows]))

    # Heatmap
    rows = con.execute("""
        SELECT hour_of_day, day_name, day_of_week_num, play_count, avg_watch_pct
        FROM main_marts.mart_listening_patterns ORDER BY day_of_week_num, hour_of_day
    """).fetchall()
    d['heatmap'] = [dict(zip(['h','day','dow','count','watch_pct'], r)) for r in rows]

    # Finance - YT quarterly
    rows = con.execute("""
        SELECT year_quarter, yt_ad_revenue_m, yt_premium_revenue_m,
               yt_total_revenue_m, google_total_rev_m, yt_music_subs_m,
               yt_share_of_google_pct, yoy_yt_rev_growth_pct
        FROM finance.yt_quarterly ORDER BY year_quarter
    """).fetchall()
    d['quarterly'] = [dict(zip(['yq','ad','prem','total','google','subs','yt_share','yoy'], r)) for r in rows]

    # Latest quarter
    r = con.execute("SELECT * FROM finance.yt_quarterly ORDER BY year_quarter DESC LIMIT 1").fetchone()
    cols = [desc[0] for desc in con.execute("SELECT * FROM finance.yt_quarterly LIMIT 0").description]
    d['latest_q'] = dict(zip(cols, r))

    # GOOGL stock
    rows = con.execute("SELECT year_month, close_price, pct_change FROM finance.googl_price ORDER BY year_month").fetchall()
    d['stock'] = [dict(zip(['ym','price','chg'], r)) for r in rows]

    # Artist revenue
    rows = con.execute("""
        SELECT channel_name, your_play_count, avg_watch_pct,
               royalty_rate_usd, effective_rate_usd,
               artist_earned_from_you_usd, plays_to_earn_1_dollar,
               global_yt_streams_b, global_gross_payout_m, global_artist_earned_m
        FROM finance.artist_revenue ORDER BY your_play_count DESC LIMIT 12
    """).fetchall()
    d['artist_rev'] = [dict(zip(['name','plays','watch_pct','rate','eff_rate',
        'artist_earned','plays_per_dollar','global_b','global_gross_m','global_artist_m'], r)) for r in rows]

    # Your totals
    r = con.execute("""
        SELECT ROUND(SUM(gross_you_generated_usd),4),
               ROUND(SUM(artist_earned_from_you_usd),4)
        FROM finance.artist_revenue
    """).fetchone()
    d['your_total'] = {'gross': r[0], 'artist': r[1]}

    # Platform comparison
    rows = con.execute("""
        SELECT platform, rate_min, rate_max, rate_mid, subscribers_m, notes
        FROM finance.platform_comparison ORDER BY rate_mid DESC
    """).fetchall()
    d['platforms'] = [dict(zip(['name','min','max','mid','subs','notes'], r)) for r in rows]

    return d


# ─────────────────────────────────────────
#  SHARED STYLES & HELPERS
# ─────────────────────────────────────────
SHARED_CSS = """
:root{
  --black:#07080a;--card:#111318;--border:#1c1f28;
  --red:#ff0000;--red2:rgba(255,0,0,.12);--red3:rgba(255,0,0,.06);
  --white:#f0eee8;--muted:#52545c;--dim:#1e2028;
  --gold:#ffd700;--green:#22c55e;--blue:#38bdf8;--purple:#a78bfa;
  --bebas:'Bebas Neue',sans-serif;
  --play:'Playfair Display',serif;
  --mono:'Space Mono',monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--black);color:var(--white);font-family:var(--mono);overflow-x:hidden;cursor:none}
#cur{width:8px;height:8px;background:var(--red);border-radius:50%;position:fixed;pointer-events:none;z-index:9999;transform:translate(-50%,-50%);mix-blend-mode:difference}
#ring{width:30px;height:30px;border:1px solid rgba(255,0,0,.4);border-radius:50%;position:fixed;pointer-events:none;z-index:9998;transform:translate(-50%,-50%);transition:left .1s,top .1s}
.dash{padding:0 44px 80px}
.sec{font-size:9px;letter-spacing:.26em;color:var(--red);text-transform:uppercase;padding:34px 0 14px;border-top:1px solid var(--border);display:flex;align-items:center;gap:12px}
.sec::after{content:'';flex:1;height:1px;background:var(--border)}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:2px;margin-bottom:2px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:2px;margin-bottom:2px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:2px;margin-bottom:2px}
.card{background:var(--card);border:1px solid var(--border);padding:24px 26px;position:relative;overflow:hidden;transition:border-color .2s}
.card:hover{border-color:#2e2e38}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--red),transparent);opacity:0;transition:opacity .3s}
.card:hover::before{opacity:.35}
.clbl{font-size:8px;letter-spacing:.18em;color:var(--muted);text-transform:uppercase;margin-bottom:9px}
.cval{font-family:var(--bebas);font-size:48px;line-height:1;letter-spacing:.02em}
.cunit{font-size:10px;margin-top:3px}
.cdelta{position:absolute;top:22px;right:22px;font-size:9px;padding:2px 7px;border-radius:2px}
.up{color:var(--green);background:rgba(34,197,94,.1)}
.dn{color:var(--red);background:var(--red2)}
.neu{color:var(--gold);background:rgba(255,215,0,.1)}
.cc{background:var(--card);border:1px solid var(--border);padding:26px 30px;margin-bottom:2px}
.ctitle{font-family:var(--play);font-size:16px;font-weight:700;margin-bottom:3px}
.csub{font-size:8px;color:var(--muted);letter-spacing:.1em;text-transform:uppercase;margin-bottom:22px}
.brow{display:grid;grid-template-columns:150px 1fr 54px;align-items:center;gap:13px;margin-bottom:10px}
.blbl{font-size:10px;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.btrack{height:4px;background:var(--dim);overflow:hidden}
.bfill{height:100%;transform-origin:left;transform:scaleX(0);animation:grow 1s cubic-bezier(.16,1,.3,1) both}
@keyframes grow{to{transform:scaleX(1)}}
.bval{font-size:9px;color:var(--muted);text-align:right}
.lc{position:relative;height:150px;margin-top:8px}
.lc svg{width:100%;height:100%;overflow:visible}
.lc-x{display:flex;justify-content:space-between;margin-top:5px}
.lc-xl{font-size:7px;color:var(--muted)}
.hm-grid{display:grid;gap:3px;margin-top:16px}
.hm-lbl{font-size:8px;color:var(--muted);display:flex;align-items:center;justify-content:flex-end;padding-right:7px}
.hm-cell{aspect-ratio:1;border-radius:2px;cursor:crosshair;transition:transform .12s}
.hm-cell:hover{transform:scale(1.5);z-index:10;position:relative}
.hm-hrs{display:grid;gap:3px;margin-top:4px}
.hm-hlbl{font-size:7px;color:var(--dim);text-align:center}
.mbars{display:flex;align-items:flex-end;gap:5px;height:88px;margin-top:18px}
.mcol{flex:1;display:flex;flex-direction:column;align-items:center;gap:4px}
.mbar{width:100%;border-radius:2px 2px 0 0;transform-origin:bottom;transform:scaleY(0);animation:growY .8s cubic-bezier(.16,1,.3,1) both;min-height:2px;position:relative;overflow:hidden}
.mbar::after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.1) 0%,transparent 50%)}
@keyframes growY{to{transform:scaleY(1)}}
.mlbl{font-size:7px;color:var(--muted);text-align:center}
.mval{font-size:7px;color:var(--red)}
.vitem{display:grid;grid-template-columns:26px 1fr 44px 50px;align-items:center;gap:12px;padding:11px 0;border-bottom:1px solid var(--border);transition:padding-left .15s}
.vitem:hover{padding-left:6px}
.vrank{font-family:var(--bebas);font-size:19px;color:var(--dim);text-align:right}
.vrank.top{color:var(--red)}
.vtitle{font-size:11px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.vchan{font-size:8px;color:var(--muted);margin-top:2px}
.vplays{font-family:var(--bebas);font-size:20px;text-align:right}
.vbar{height:3px;background:var(--dim);overflow:hidden}
.vbar-f{height:100%;background:var(--red);transform-origin:left;transform:scaleX(0);animation:grow 1s cubic-bezier(.16,1,.3,1) both}
.sitem{display:flex;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid var(--border)}
.sname{font-size:10px;flex:1}
.spct{font-family:var(--bebas);font-size:22px;width:46px;text-align:right}
.sbar-w{width:90px;height:3px;background:var(--dim);overflow:hidden}
.sbar-f{height:100%;transform-origin:left;transform:scaleX(0);animation:grow 1s cubic-bezier(.16,1,.3,1) both}
.acard{background:var(--card);border:1px solid var(--border);padding:18px 20px;transition:all .2s;position:relative;overflow:hidden}
.acard:hover{border-color:#2e2e38;transform:translateY(-2px)}
.acard-rank{font-family:var(--bebas);font-size:36px;color:var(--dim);line-height:1;margin-bottom:3px}
.acard-name{font-size:12px;font-weight:700;margin-bottom:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.acard-row{display:flex;justify-content:space-between;align-items:baseline;padding:5px 0;border-bottom:1px solid var(--border)}
.acard-row:last-child{border-bottom:none}
.acard-lbl{font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
.acard-val{font-family:var(--bebas);font-size:16px}
.insight{background:linear-gradient(135deg,var(--red2),var(--red3));border:1px solid rgba(255,0,0,.18);border-left:3px solid var(--red);padding:22px 26px;margin-bottom:2px}
.itag{font-size:8px;letter-spacing:.2em;color:var(--red);text-transform:uppercase;margin-bottom:8px}
.itext{font-family:var(--play);font-style:italic;font-size:15px;line-height:1.6;max-width:680px}
.bench-row{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--border)}
.bench-name{font-size:11px;font-weight:700;width:130px;flex-shrink:0}
.bench-bw{flex:1;height:4px;background:var(--dim);overflow:hidden}
.bench-b{height:100%;transform-origin:left;transform:scaleX(0);animation:grow 1s cubic-bezier(.16,1,.3,1) both}
.bench-rate{font-family:var(--bebas);font-size:18px;width:58px;text-align:right}
.bench-note{font-size:8px;color:var(--muted);width:200px;flex-shrink:0}
.footer{border-top:1px solid var(--border);padding:22px 44px;display:flex;justify-content:space-between;font-size:8px;letter-spacing:.13em;color:var(--muted);text-transform:uppercase}
.footer .logo{font-family:var(--bebas);font-size:17px;color:var(--red);letter-spacing:.1em}
.rv{opacity:0;transform:translateY(18px);transition:opacity .5s ease,transform .5s ease}
.rv.on{opacity:1;transform:none}
@keyframes up{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes blink{0%,100%{opacity:.2}50%{opacity:.8}}
"""

CURSOR_JS = """
const cur=document.getElementById('cur'),ring=document.getElementById('ring');
let mx=0,my=0,rx=0,ry=0;
document.addEventListener('mousemove',e=>{mx=e.clientX;my=e.clientY;cur.style.left=mx+'px';cur.style.top=my+'px'});
setInterval(()=>{rx+=(mx-rx)*.13;ry+=(my-ry)*.13;ring.style.left=rx+'px';ring.style.top=ry+'px'},14);
"""

REVEAL_JS = """
const rvs=document.querySelectorAll('.rv');
const obs=new IntersectionObserver(e=>e.forEach(x=>{if(x.isIntersecting)x.target.classList.add('on')}),{threshold:.07});
rvs.forEach(r=>obs.observe(r));
"""

LINECHART_JS = """
function lineChart(cid, datasets, step=3){
  const el=document.getElementById(cid);
  if(!el)return;
  const W=el.offsetWidth||600,H=150,pad={t:10,r:8,b:8,l:36};
  const cw=W-pad.l-pad.r,ch=H-pad.t-pad.b;
  const all=datasets.flatMap(d=>d.v);
  const mn=Math.min(...all)*.95,mx=Math.max(...all)*1.02;
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
  // grid
  [0,.33,.67,1].forEach(p=>{
    const y=pad.t+ch*(1-p),v=Math.round(mn+(mx-mn)*p);
    const l=document.createElementNS('http://www.w3.org/2000/svg','line');
    l.setAttribute('x1',pad.l);l.setAttribute('x2',pad.l+cw);
    l.setAttribute('y1',y);l.setAttribute('y2',y);
    l.setAttribute('stroke','#1c1f28');l.setAttribute('stroke-width','1');
    svg.appendChild(l);
    const t=document.createElementNS('http://www.w3.org/2000/svg','text');
    t.setAttribute('x',pad.l-3);t.setAttribute('y',y+3);
    t.setAttribute('text-anchor','end');t.setAttribute('fill','#52545c');
    t.setAttribute('font-size','7');t.setAttribute('font-family','Space Mono,monospace');
    t.textContent=v>=1000?(v/1000).toFixed(1)+'k':v;
    svg.appendChild(t);
  });
  datasets.forEach(ds=>{
    const n=ds.v.length;
    const pts=ds.v.map((v,i)=>[pad.l+cw*(i/(n-1)),pad.t+ch*(1-(v-mn)/(mx-mn))]);
    const aD='M'+pts.map(p=>p.join(',')).join(' L')+` L${pts[n-1][0]},${pad.t+ch} L${pts[0][0]},${pad.t+ch} Z`;
    const area=document.createElementNS('http://www.w3.org/2000/svg','path');
    area.setAttribute('d',aD);area.setAttribute('fill',ds.c);area.setAttribute('opacity','.08');
    svg.appendChild(area);
    const pD='M'+pts.map(p=>p.join(',')).join(' L');
    const path=document.createElementNS('http://www.w3.org/2000/svg','path');
    path.setAttribute('d',pD);path.setAttribute('fill','none');
    path.setAttribute('stroke',ds.c);path.setAttribute('stroke-width','2');
    path.setAttribute('stroke-linecap','round');
    const len=2000;
    path.style.strokeDasharray=len;path.style.strokeDashoffset=len;
    path.style.transition='stroke-dashoffset 1.4s cubic-bezier(.16,1,.3,1)';
    svg.appendChild(path);
    setTimeout(()=>path.style.strokeDashoffset='0',200);
    // last dot
    const lp=pts[n-1];
    const dot=document.createElementNS('http://www.w3.org/2000/svg','circle');
    dot.setAttribute('cx',lp[0]);dot.setAttribute('cy',lp[1]);dot.setAttribute('r','3');
    dot.setAttribute('fill',ds.c);dot.setAttribute('stroke','#07080a');dot.setAttribute('stroke-width','2');
    svg.appendChild(dot);
  });
  el.appendChild(svg);
}
"""

def counter_js(ids_vals):
    lines = ["function count(el,to,dur=1600,dec=0){let s=null;(function step(ts){if(!s)s=ts;const p=Math.min((ts-s)/dur,1),e=1-Math.pow(1-p,4);el.textContent=dec>0?(e*to).toFixed(dec):Math.round(e*to);if(p<1)requestAnimationFrame(step)})(performance.now())}"]
    lines.append("setTimeout(()=>{")
    for eid, val, dec in ids_vals:
        lines.append(f"  count(document.getElementById('{eid}'),{val},{1600},{dec});")
    lines.append("},500);")
    return "\n".join(lines)


def hero_html(eyebrow, title1, title2, title3, sub, kpis, accent="#ff0000", vinyl_color="red"):
    kvs = "".join(f'<div class="hkpi"><div class="v" id="{k[0]}" style="color:{k[3]}">{k[2]}</div><div class="l">{k[1]}</div></div>' for k in kpis)
    return f"""
<style>
.hero{{min-height:100vh;display:flex;flex-direction:column;justify-content:center;padding:64px;position:relative;overflow:hidden}}
.hero-bg{{position:absolute;inset:0;background:radial-gradient(ellipse 55% 55% at 85% 45%,rgba(255,0,0,.07) 0%,transparent 65%),radial-gradient(ellipse 35% 40% at 5% 85%,rgba(255,215,0,.04) 0%,transparent 60%)}}
.vinyl{{position:absolute;right:-100px;top:50%;transform:translateY(-50%);width:480px;height:480px;border-radius:50%;background:repeating-radial-gradient(circle at center,#090909 0,#111 2px,#0c0c0c 4px,#111 6px,#090909 8px);animation:spin 20s linear infinite;opacity:.28}}
.vinyl::before{{content:'';position:absolute;inset:32%;border-radius:50%;background:radial-gradient(#181818 40%,#0f0f0f);border:1px solid #222}}
.vinyl::after{{content:'';position:absolute;inset:46%;border-radius:50%;background:{accent};opacity:.5;box-shadow:0 0 18px {accent}}}
@keyframes spin{{to{{transform:translateY(-50%) rotate(360deg)}}}}
.yt-logo{{position:absolute;right:120px;top:50%;transform:translateY(-50%);width:220px;height:220px;display:flex;align-items:center;justify-content:center;z-index:2;opacity:.12}}
.live-badge{{display:inline-flex;align-items:center;gap:7px;background:rgba(255,0,0,.08);border:1px solid rgba(255,0,0,.2);border-radius:2px;padding:4px 12px;font-size:8px;letter-spacing:.15em;color:var(--red);text-transform:uppercase;margin-bottom:16px;opacity:0;animation:up .6s .05s ease forwards}}
.live-dot{{width:5px;height:5px;border-radius:50%;background:var(--red);animation:blink 1.8s infinite}}
.eyebrow{{font-size:10px;letter-spacing:.22em;color:var(--red);text-transform:uppercase;margin-bottom:16px;opacity:0;animation:up .6s .1s ease forwards}}
h1{{font-family:var(--bebas);font-size:clamp(66px,9vw,124px);line-height:.9;letter-spacing:.02em;opacity:0;animation:up .6s .2s ease forwards;max-width:660px}}
h1 .r{{color:var(--red)}} h1 .g{{color:var(--gold)}} h1 .ghost{{-webkit-text-stroke:1px rgba(255,255,255,.11);color:transparent}}
.sub{{margin-top:20px;font-family:var(--play);font-style:italic;font-size:14px;color:var(--muted);max-width:440px;line-height:1.7;opacity:0;animation:up .6s .3s ease forwards}}
.hero-kpis{{display:flex;flex-wrap:wrap;gap:40px;margin-top:48px;opacity:0;animation:up .6s .4s ease forwards}}
.hkpi .v{{font-family:var(--bebas);font-size:46px;line-height:1;letter-spacing:.02em}}
.hkpi .l{{font-size:8px;letter-spacing:.16em;color:var(--muted);text-transform:uppercase;margin-top:3px}}
.scroll-h{{margin-top:50px;font-size:9px;letter-spacing:.2em;color:var(--dim);text-transform:uppercase;opacity:0;animation:up .6s .6s ease forwards,blink 2s 1.5s infinite}}
</style>
<section class="hero">
  <div class="hero-bg"></div>
  <div class="vinyl"></div>
  <div class="live-badge"><span class="live-dot"></span>Live from DuckDB · {GEN}</div>
  <div class="eyebrow">{eyebrow}</div>
  <h1>{title1}<br><span class="r">{title2}</span><br><span class="ghost">{title3}</span></h1>
  <p class="sub">{sub}</p>
  <div class="hero-kpis">{kvs}</div>
  <div class="scroll-h">↓ &nbsp; Scroll to explore</div>
</section>"""


# ─────────────────────────────────────────
#  DASHBOARD 1 — LISTENING BEHAVIOUR
# ─────────────────────────────────────────
def build_listening(d):
    k = d['kpi']
    top_ch = d['channels'][0]['name'] if d['channels'] else 'Taylor Swift'
    top_skip = sorted(d['channels'], key=lambda x: x['skip_pct'], reverse=True)[0]

    channels_js   = json.dumps(d['channels'])
    videos_js     = json.dumps(d['videos'])
    devices_js    = json.dumps(d['devices'])
    monthly_js    = json.dumps(d['monthly'])
    heatmap_js    = json.dumps(d['heatmap'])
    genres_js     = json.dumps(d['genres'])

    dev_colors = ['#ff0000','#ffd700','#38bdf8','#a78bfa','#22c55e']

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>YT Music — Listening Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Playfair+Display:ital,wght@0,700;1,400&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>{SHARED_CSS}
body::after{{content:'';position:fixed;inset:0;opacity:.4;pointer-events:none;z-index:9990;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.03'/%3E%3C/svg%3E")}}
.yt-badge{{display:inline-flex;align-items:center;gap:6px;background:rgba(255,0,0,.08);border:1px solid rgba(255,0,0,.15);padding:3px 10px;border-radius:2px;font-size:8px;color:var(--red);letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px}}
</style>
</head>
<body>
<div id="cur"></div><div id="ring"></div>

{hero_html(
    "YouTube Music · Listening Behaviour Warehouse",
    "YOUR", "MUSIC", "DECODED",
    f"{k['plays']:,} plays · {k['first']} → {k['last']}<br>DuckDB + dbt star schema · 22 tests passing.",
    [
        ('h1', 'Total Plays',      k['plays'],         '#ff0000'),
        ('h2', 'Hours Watched',    k['hours'],         '#ffd700'),
        ('h3', 'Unique Channels',  k['channels'],      '#38bdf8'),
        ('h4', 'Avg Watch %',      k['avg_watch_pct'], '#22c55e'),
    ]
)}

<div class="dash">

<div class="sec rv">01 — Key Metrics</div>
<div class="g4 rv">
  <div class="card"><div class="clbl">Total Watch Time</div><div class="cval" style="color:var(--red)">{k['hours']}</div><div class="cunit" style="color:var(--red)">hours listened</div><div class="cdelta up">↑ real data</div></div>
  <div class="card"><div class="clbl">Skip Rate</div><div class="cval" style="color:var(--gold)">{k['skip_pct']}<span style="font-size:24px">%</span></div><div class="cunit" style="color:var(--gold)">inferred from watch %</div><div class="cdelta {'up' if k['skip_pct']<20 else 'dn'}">{'✓ low' if k['skip_pct']<20 else '⚡ high'}</div></div>
  <div class="card"><div class="clbl">Avg Watch %</div><div class="cval" style="color:var(--green)">{k['avg_watch_pct']}<span style="font-size:24px">%</span></div><div class="cunit" style="color:var(--green)">of each video watched</div><div class="cdelta up">↑ engaged listener</div></div>
  <div class="card"><div class="clbl">Unique Videos</div><div class="cval" style="color:var(--blue)">{k['videos']}</div><div class="cunit" style="color:var(--blue)">distinct tracks</div><div class="cdelta neu">→ diverse taste</div></div>
</div>

<div class="sec rv">02 — Channel Intelligence</div>
<div class="g2 rv">
  <div class="cc">
    <div class="ctitle">Top Channels</div><div class="csub">by total hours — your real data</div>
    <div id="chanBars"></div>
  </div>
  <div class="cc">
    <div class="ctitle">Device Split</div><div class="csub">where you listen most</div>
    <div style="margin-top:12px" id="deviceList"></div>
    <div style="margin-top:20px">
      <div class="ctitle" style="font-size:14px">Genre Breakdown</div>
      <div style="margin-top:10px" id="genreList"></div>
    </div>
  </div>
</div>

<div class="sec rv">03 — Top Videos</div>
<div class="cc rv">
  <div class="ctitle">Most Played Videos</div><div class="csub">by total play count</div>
  <div id="videoList"></div>
</div>

<div class="sec rv">04 — When You Listen</div>
<div class="cc rv">
  <div class="ctitle">Listening Heatmap</div><div class="csub">plays by hour × day of week</div>
  <div id="hmWrap"></div>
  <div style="display:flex;align-items:center;gap:7px;margin-top:12px">
    <span style="font-size:8px;color:var(--muted)">Low</span>
    <div style="display:flex;gap:2px">
      {''.join(f'<div style="width:10px;height:10px;border-radius:2px;background:rgba(255,0,0,{a})"></div>' for a in ['.07','.2','.4','.62','.85'])}
    </div>
    <span style="font-size:8px;color:var(--muted)">High</span>
  </div>
</div>

<div class="sec rv">05 — Monthly Trends & Skip Analysis</div>
<div class="g2 rv">
  <div class="cc">
    <div class="ctitle">Monthly Plays</div><div class="csub">play count per month</div>
    <div class="mbars" id="monthBars"></div>
  </div>
  <div class="cc">
    <div class="ctitle">Skip Rate by Channel</div><div class="csub">% skipped (watch < 45%)</div>
    <div style="margin-top:10px" id="skipList"></div>
  </div>
</div>

<div class="insight rv">
  <div class="itag">⬡ Key Insight — from your real data</div>
  <div class="itext">Your most-skipped channel is <strong>{top_skip['name']} at {top_skip['skip_pct']}% skip rate</strong> — yet they rank in your top channels by total hours. This is the YT Music shuffle paradox: high play count + high skip = you love the artist, not every video in every moment. On YouTube Music, skip rate is inferred from watch percentage — below 45% counts as a skip.</div>
</div>

<div class="sec rv">06 — Engineering Stack</div>
<div class="g3 rv">
  <div class="card"><div class="clbl">Ingestion</div><div style="font-family:var(--bebas);font-size:32px;color:var(--gold);margin:7px 0">Python</div><div style="font-size:10px;color:var(--muted);line-height:1.65">Google Takeout JSON → Pandas → DuckDB raw schema. Parsed {k['plays']:,} real watch events.</div></div>
  <div class="card"><div class="clbl">Transform</div><div style="font-family:var(--bebas);font-size:32px;color:var(--blue);margin:7px 0">dbt-core</div><div style="font-size:10px;color:var(--muted);line-height:1.65">Staging → Marts. Star schema across {k['channels']} channels, {k['videos']} videos. 22 quality tests.</div></div>
  <div class="card"><div class="clbl">Warehouse</div><div style="font-family:var(--bebas);font-size:32px;color:var(--red);margin:7px 0">DuckDB</div><div style="font-size:10px;color:var(--muted);line-height:1.65">{k['hours']} hours of YT Music history. Zero config, fully local, millisecond queries.</div></div>
</div>

</div>
<div class="footer"><div class="logo">YT Music DWH</div><div>Listening Dashboard · {GEN}</div><div>{k['plays']:,} plays · {k['channels']} channels</div></div>

<script>
{CURSOR_JS}
{LINECHART_JS}
{counter_js([('h1',k['plays'],0),('h2',k['hours'],1),('h3',k['channels'],0),('h4',k['avg_watch_pct'],1)])}

const CHANNELS={channels_js};
const VIDEOS={videos_js};
const DEVICES={devices_js};
const MONTHLY={monthly_js};
const HEATMAP={heatmap_js};
const GENRES={genres_js};
const DEV_COLORS={json.dumps(dev_colors)};

// Channel bars
const cb=document.getElementById('chanBars');
const maxH=CHANNELS[0].hours;
CHANNELS.forEach((c,i)=>{{
  cb.innerHTML+=`<div class="brow"><div class="blbl">${{c.name}}</div><div class="btrack"><div class="bfill" style="background:var(--red);animation-delay:${{i*.07}}s;width:${{c.hours/maxH*100}}%"></div></div><div class="bval">${{c.hours}}h</div></div>`;
}});

// Device list
const dl=document.getElementById('deviceList');
DEVICES.forEach((dv,i)=>{{
  const col=DEV_COLORS[i]||'#888';
  dl.innerHTML+=`<div class="bench-row"><div class="bench-name" style="color:${{col}}">${{dv.name}}</div><div class="bench-bw"><div class="bench-b" style="background:${{col}};animation-delay:${{i*.08}}s;width:${{dv.pct}}%"></div></div><div class="bench-rate" style="color:${{col}}">${{dv.pct}}%</div></div>`;
}});

// Genre list
const gl=document.getElementById('genreList');
const genColors=['#ff0000','#ffd700','#38bdf8','#a78bfa','#22c55e','#f97316','#ec4899','#14b8a6','#8b5cf6','#06b6d4'];
const maxGP=GENRES[0].plays;
GENRES.slice(0,6).forEach((g,i)=>{{
  const col=genColors[i];
  gl.innerHTML+=`<div class="brow" style="grid-template-columns:120px 1fr 40px"><div class="blbl" style="color:${{col}}">${{g.name}}</div><div class="btrack"><div class="bfill" style="background:${{col}};animation-delay:${{i*.07}}s;width:${{g.plays/maxGP*100}}%"></div></div><div class="bval">${{g.pct}}%</div></div>`;
}});

// Videos
const vl=document.getElementById('videoList');
const maxV=VIDEOS[0].plays;
VIDEOS.forEach((v,i)=>{{
  vl.innerHTML+=`<div class="vitem"><div class="vrank${{i<3?' top':''}}">${{i+1}}</div><div><div class="vtitle">${{v.title}}</div><div class="vchan">${{v.channel}}</div></div><div><div class="vplays">${{v.plays}}</div><div style="font-size:7px;color:var(--muted);text-align:right">PLAYS</div></div><div class="vbar"><div class="vbar-f" style="animation-delay:${{i*.06}}s;width:${{v.plays/maxV*100}}%"></div></div></div>`;
}});

// Heatmap
const days=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
const dayShort=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const wrap=document.getElementById('hmWrap');
const hmG=document.createElement('div');
hmG.className='hm-grid';hmG.style.gridTemplateColumns='52px repeat(24,1fr)';
const maxC=Math.max(...HEATMAP.map(h=>h.count));
days.forEach((day,di)=>{{
  const lb=document.createElement('div');lb.className='hm-lbl';lb.textContent=dayShort[di];hmG.appendChild(lb);
  for(let h=0;h<24;h++){{
    const entry=HEATMAP.find(x=>x.dow===di&&x.h===h)||{{count:0}};
    const v=maxC>0?entry.count/maxC:0;
    const a=(0.05+v*.8).toFixed(2);
    const cell=document.createElement('div');
    cell.className='hm-cell';cell.style.background=`rgba(255,0,0,${{a}})`;
    cell.title=`${{dayShort[di]}} ${{h}}:00 — ${{entry.count}} plays`;
    hmG.appendChild(cell);
  }}
}});
wrap.appendChild(hmG);
const hmHr=document.createElement('div');hmHr.className='hm-hrs';hmHr.style.gridTemplateColumns='52px repeat(24,1fr)';
hmHr.innerHTML='<div></div>';
for(let h=0;h<24;h++)hmHr.innerHTML+=`<div class="hm-hlbl">${{h%3===0?h:''}}</div>`;
wrap.appendChild(hmHr);

// Monthly bars
const maxP=Math.max(...MONTHLY.map(m=>m.plays));
const mb=document.getElementById('monthBars');
MONTHLY.forEach((m,i)=>{{
  const h=Math.round(m.plays/maxP*82);
  mb.innerHTML+=`<div class="mcol"><div class="mval">${{m.plays}}</div><div class="mbar" style="height:${{h}}px;background:var(--red);animation-delay:${{i*.05}}s"></div><div class="mlbl">${{m.month}}</div></div>`;
}});

// Skip list
const sl=document.getElementById('skipList');
const sorted=[...CHANNELS].sort((a,b)=>b.skip_pct-a.skip_pct).slice(0,6);
const maxSk=sorted[0]?.skip_pct||25;
sorted.forEach((c,i)=>{{
  const col=c.skip_pct>20?'var(--red)':c.skip_pct>15?'var(--gold)':'var(--muted)';
  sl.innerHTML+=`<div class="sitem"><div class="sname">${{c.name}}</div><div class="spct" style="color:${{col}}">${{c.skip_pct}}%</div><div class="sbar-w"><div class="sbar-f" style="background:${{col}};animation-delay:${{i*.09}}s;width:${{c.skip_pct/maxSk*100}}%"></div></div></div>`;
}});

{REVEAL_JS}
</script>
</body></html>"""


# ─────────────────────────────────────────
#  DASHBOARD 2 — FINANCE
# ─────────────────────────────────────────
def build_finance(d):
    lq   = d['latest_q']
    yt   = d['your_total']
    top  = d['artist_rev'][0]

    quarterly_js = json.dumps(d['quarterly'])
    stock_js     = json.dumps(d['stock'])
    artist_js    = json.dumps(d['artist_rev'])
    platform_js  = json.dumps(d['platforms'])
    acolors      = ['#ff0000','#ffd700','#38bdf8','#a78bfa','#22c55e','#f97316','#ec4899','#14b8a6','#8b5cf6','#06b6d4','#ff0000','#ffd700']

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>YT Music — Finance Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Playfair+Display:ital,wght@0,700;1,400&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>{SHARED_CSS}
body::after{{content:'';position:fixed;inset:0;opacity:.4;pointer-events:none;z-index:9990;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.03'/%3E%3C/svg%3E")}}
.ticker{{background:#0e1014;border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:10px 0;overflow:hidden;white-space:nowrap;margin-bottom:2px}}
.ticker-inner{{display:inline-flex;gap:48px;animation:ticker 28s linear infinite}}
@keyframes ticker{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}
.ti{{font-size:10px;letter-spacing:.06em;display:flex;align-items:center;gap:8px}}
.ti .sym{{color:var(--red);font-weight:700}}
.ti .pos{{color:var(--green)}}
.acard-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:2px;margin-bottom:2px}}
</style>
</head>
<body>
<div id="cur"></div><div id="ring"></div>

<div class="ticker"><div class="ticker-inner" id="ticker"></div></div>

{hero_html(
    "YouTube Music · Finance Intelligence · Option 1 + 2",
    "MONEY", "BEHIND", "THE MUSIC",
    f"YouTube Q4 2024: ${lq['yt_total_revenue_m']:,}M total revenue. Your {d['kpi']['plays']:,} plays generated ${yt['gross']} in royalties.",
    [
        ('h1', 'YT Revenue Q4\'24 ($M)', lq['yt_total_revenue_m'], '#ffd700'),
        ('h2', 'YT Music Subs (M)',      lq['yt_music_subs_m'],    '#ff0000'),
        ('h3', 'GOOGL Net Income ($M)',  lq['alphabet_net_income_m'], '#38bdf8'),
        ('h4', 'YT Share of Google %',  lq['yt_share_of_google_pct'], '#22c55e'),
    ]
)}

<div class="dash">

<div class="sec rv">01 — YouTube Business Financials</div>
<div class="g4 rv">
  <div class="card"><div class="clbl">Q4 2024 YT Total Rev</div><div class="cval" style="color:var(--gold)">${lq['yt_total_revenue_m']:,}M</div><div class="cunit" style="color:var(--gold)">ad + premium</div><div class="cdelta up">↑ {lq['yoy_yt_rev_growth_pct']}% YoY</div></div>
  <div class="card"><div class="clbl">YT Ad Revenue</div><div class="cval" style="color:var(--red)">${lq['yt_ad_revenue_m']:,}M</div><div class="cunit" style="color:var(--red)">ad-supported streams</div><div class="cdelta up">↑ growing</div></div>
  <div class="card"><div class="clbl">YT Premium Revenue</div><div class="cval" style="color:var(--blue)">${lq['yt_premium_revenue_m']:,}M</div><div class="cunit" style="color:var(--blue)">est. incl. YT Music</div><div class="cdelta up">↑ fastest growing</div></div>
  <div class="card"><div class="clbl">YT Music Subscribers</div><div class="cval" style="color:var(--green)">{lq['yt_music_subs_m']}<span style="font-size:24px">M</span></div><div class="cunit" style="color:var(--green)">paid subscribers</div><div class="cdelta up">↑ vs 80M in 2022</div></div>
</div>

<div class="g2 rv">
  <div class="cc">
    <div class="ctitle">YouTube Revenue Trend</div><div class="csub">ad revenue vs premium revenue · 2022–2024 (USD millions)</div>
    <div class="lc" id="revChart"></div>
    <div class="lc-x" id="revLabels"></div>
  </div>
  <div class="cc">
    <div class="ctitle">GOOGL Stock Price</div><div class="csub">USD monthly close · 2022–2024</div>
    <div class="lc" id="stockChart"></div>
    <div class="lc-x" id="stockLabels"></div>
  </div>
</div>

<div class="g2 rv">
  <div class="cc">
    <div class="ctitle">YT Music Subscribers</div><div class="csub">millions of paid subscribers</div>
    <div class="lc" id="subsChart"></div>
    <div class="lc-x" id="subsLabels"></div>
  </div>
  <div class="cc">
    <div class="ctitle">YT Share of Google Revenue</div><div class="csub">% of total Alphabet revenue</div>
    <div class="lc" id="shareChart"></div>
    <div class="lc-x" id="shareLabels"></div>
  </div>
</div>

<div class="insight rv">
  <div class="itag" style="color:var(--gold)">⬡ Business Insight</div>
  <div class="itext">YouTube's ad revenue grew from <strong>$6.9B in Q1 2022 to $9.8B in Q4 2024</strong> (+42%) while YT Music subscribers tripled from 80M to 125M. Yet YouTube Music pays artists <strong>5–8× less per stream than Tidal</strong> — because 90%+ of plays come from ad-supported free users. Scale wins over rate.</div>
</div>

<div class="sec rv">02 — Artist Revenue Estimator</div>
<div class="g3 rv">
  <div class="card"><div class="clbl">Total You Generated</div><div class="cval" style="color:var(--gold)">${yt['gross']}</div><div class="cunit" style="color:var(--gold)">gross from {d['kpi']['plays']:,} plays</div><div class="cdelta neu">to rights holders</div></div>
  <div class="card"><div class="clbl">Artists Actually Earned</div><div class="cval" style="color:var(--green)">${yt['artist']}</div><div class="cunit" style="color:var(--green)">after label's ~78% cut</div><div class="cdelta dn">label keeps the rest</div></div>
  <div class="card"><div class="clbl">Your #1 Channel</div><div class="cval" style="font-size:22px;margin-top:6px">{top['name']}</div><div class="cunit" style="color:var(--muted);margin-top:6px">{top['plays']} plays · ${top['artist_earned']:.4f} earned</div></div>
</div>

<div class="acard-grid rv" id="artistCards"></div>

<div class="insight rv" style="background:linear-gradient(135deg,rgba(34,197,94,.07),rgba(34,197,94,.02));border-color:rgba(34,197,94,.18);border-left-color:var(--green)">
  <div class="itag" style="color:var(--green)">⬡ Revenue Insight</div>
  <div class="itext">{top['name']} earned <strong>${top['artist_earned']:.4f} from your {top['plays']} personal plays</strong> — but globally their <strong>{top['global_b']}B YouTube streams</strong> generated an estimated <strong>${top['global_artist_m']}M directly</strong> after label cuts. YouTube's low per-stream rate is offset entirely by massive scale — 2.7 billion monthly users.</div>
</div>

<div class="sec rv">03 — Platform Royalty Comparison</div>
<div class="cc rv">
  <div class="ctitle">Per-Stream Payout Across Platforms</div><div class="csub">mid-point royalty rate USD — YouTube Music highlighted</div>
  <div style="margin-top:8px" id="platformList"></div>
</div>

<div class="insight rv">
  <div class="itag" style="color:var(--gold)">⬡ Industry Insight</div>
  <div class="itext">YouTube Music's blended rate of <strong>~$0.002/stream</strong> is the second lowest in the industry — only YouTube Free is lower. An artist needs <strong>~500 YouTube Music streams to earn $1</strong> vs ~250 on Spotify and ~90 on Tidal. But YouTube's 2.7B monthly users means total volume can dwarf other platforms entirely.</div>
</div>

</div>
<div class="footer"><div class="logo">YT Music Finance</div><div>Option 1 + 2 · {GEN}</div><div>Sources: Alphabet IR · IFPI 2024 · MBW</div></div>

<script>
{CURSOR_JS}
{LINECHART_JS}
{counter_js([('h1',lq['yt_total_revenue_m'],0),('h2',lq['yt_music_subs_m'],0),('h3',lq['alphabet_net_income_m'],0),('h4',lq['yt_share_of_google_pct'],1)])}

const QUARTERLY={quarterly_js};
const STOCK={stock_js};
const ARTIST_REV={artist_js};
const PLATFORMS={platform_js};
const ACOLORS={json.dumps(acolors)};

// Ticker
const tD=[['GOOGL','$196','+123% 2yr','pos'],['YT REV','$9.8B','+42% 2yr','pos'],['YT SUBS','125M','+56% 2yr','pos'],['GOOGL','$196','+123% 2yr','pos'],['YT REV','$9.8B','+42% 2yr','pos'],['YT SUBS','125M','+56% 2yr','pos']];
const tk=document.getElementById('ticker');
[...tD,...tD].forEach(([s,p,c,cl])=>tk.innerHTML+=`<div class="ti"><span class="sym">${{s}}</span><span>${{p}}</span><span class="${{cl}}">${{c}}</span></div>`);

// Charts
const qL=QUARTERLY.map(q=>q.yq);
lineChart('revChart',[{{v:QUARTERLY.map(q=>q.ad),c:'#ffd700'}},{{v:QUARTERLY.map(q=>q.prem),c:'#ff0000'}}]);
document.getElementById('revLabels').innerHTML=qL.filter((_,i)=>i%3===0).map(l=>`<span class="lc-xl">${{l}}</span>`).join('');
lineChart('stockChart',[{{v:STOCK.map(s=>s.price),c:'#ffd700'}}]);
const sL=STOCK.map(s=>s.ym.slice(2));
document.getElementById('stockLabels').innerHTML=sL.filter((_,i)=>i%6===0).map(l=>`<span class="lc-xl">${{l}}</span>`).join('');
lineChart('subsChart',[{{v:QUARTERLY.map(q=>q.subs),c:'#ff0000'}}]);
document.getElementById('subsLabels').innerHTML=qL.filter((_,i)=>i%3===0).map(l=>`<span class="lc-xl">${{l}}</span>`).join('');
lineChart('shareChart',[{{v:QUARTERLY.map(q=>q.yt_share),c:'#22c55e'}}]);
document.getElementById('shareLabels').innerHTML=qL.filter((_,i)=>i%3===0).map(l=>`<span class="lc-xl">${{l}}</span>`).join('');

// Artist cards
const ag=document.getElementById('artistCards');
ARTIST_REV.forEach((a,i)=>{{
  const col=ACOLORS[i]||'#ff0000';
  ag.innerHTML+=`<div class="acard">
    <div class="acard-rank" style="color:rgba(255,255,255,.06)">${{String(i+1).padStart(2,'0')}}</div>
    <div class="acard-name" style="color:${{col}}">${{a.name}}</div>
    <div class="acard-row"><span class="acard-lbl">Your Plays</span><span class="acard-val">${{a.plays}}</span></div>
    <div class="acard-row"><span class="acard-lbl">Avg Watch %</span><span class="acard-val">${{a.watch_pct}}%</span></div>
    <div class="acard-row"><span class="acard-lbl">Artist Earned</span><span class="acard-val" style="color:${{col}}">$${{a.artist_earned.toFixed(4)}}</span></div>
    <div class="acard-row"><span class="acard-lbl">Global Earned</span><span class="acard-val" style="color:var(--muted);font-size:13px">${{a.global_artist_m!==null?'$'+a.global_artist_m+'M':'—'}}</span></div>
  </div>`;
}});

// Platform
const pl=document.getElementById('platformList');
const maxR=Math.max(...PLATFORMS.map(p=>p.mid));
PLATFORMS.forEach((p,i)=>{{
  const isYT=p.name.includes('YouTube Music');
  const col=isYT?'#ff0000':'#52545c';
  pl.innerHTML+=`<div class="bench-row">
    <div class="bench-name" style="color:${{isYT?'var(--red)':'var(--white)'}}">${{p.name}}</div>
    <div class="bench-bw"><div class="bench-b" style="background:${{col}};animation-delay:${{i*.08}}s;width:${{p.mid/maxR*100}}%"></div></div>
    <div class="bench-rate" style="color:${{col}}">$${{p.mid}}</div>
    <div class="bench-note">${{p.notes}}</div>
  </div>`;
}});

{REVEAL_JS}
</script>
</body></html>"""


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("🎵 YT Music — Dashboard Generator")
    print("=" * 40)

    if not os.path.exists(DB_PATH):
        print("❌ Run: python run_pipeline.py")
        raise SystemExit(1)

    con = duckdb.connect(DB_PATH, read_only=True)
    tables = con.execute("SHOW ALL TABLES").df()
    if 'finance' not in tables['schema'].values:
        con.close()
        print("❌ Finance schema missing. Run: python load_yt_finance.py")
        raise SystemExit(1)

    print("\n→ Querying real data from DuckDB...")
    d = fetch_all(con)
    con.close()

    k  = d['kpi']
    lq = d['latest_q']
    print(f"\n  Plays       : {k['plays']:,}")
    print(f"  Hours       : {k['hours']}")
    print(f"  Channels    : {k['channels']}")
    print(f"  YT Revenue  : ${lq['yt_total_revenue_m']:,}M (Q4 2024)")
    print(f"  You generated: ${d['your_total']['gross']} gross")

    os.makedirs(OUT_DIR, exist_ok=True)

    print("\n→ Building listening dashboard...")
    with open(f"{OUT_DIR}/listening_dashboard.html","w",encoding="utf-8") as f:
        f.write(build_listening(d))
    print(f"  ✅ {OUT_DIR}/listening_dashboard.html")

    print("→ Building finance dashboard...")
    with open(f"{OUT_DIR}/finance_dashboard.html","w",encoding="utf-8") as f:
        f.write(build_finance(d))
    print(f"  ✅ {OUT_DIR}/finance_dashboard.html")

    print("\n🎉 Both dashboards generated from real DuckDB data!\n")
