"""generate_finance_dashboard.py — YT Music Finance Dashboard"""
import duckdb, json, os
from datetime import datetime

DB_PATH = "data/ytmusic.duckdb"
OUTPUT  = "dashboard/yt_finance_dashboard.html"

def fetch(con):
    d = {}
    r = con.execute("SELECT yt_ad_revenue_m,op_margin_pct,yoy_yt_growth_pct,alphabet_revenue_m,operating_income_m FROM finance.yt_quarterly ORDER BY year_quarter DESC LIMIT 1").fetchone()
    d['latest'] = dict(zip(['yt_rev','op_margin','yoy','alpha_rev','op_inc'], r))

    rows = con.execute("SELECT year_quarter,yt_ad_revenue_m,alphabet_revenue_m,op_margin_pct,yt_revenue_share_pct,yoy_yt_growth_pct FROM finance.yt_quarterly ORDER BY year_quarter").fetchall()
    d['quarterly'] = [dict(zip(['yq','yt_rev','alpha_rev','op_margin','yt_share','yoy'],r)) for r in rows]

    rows = con.execute("SELECT year_month,close_price,price_change_pct FROM finance.googl_price_history ORDER BY year_month").fetchall()
    d['stock'] = [dict(zip(['ym','price','chg'],r)) for r in rows]

    rows = con.execute("SELECT channel_name,your_play_count,avg_watch_pct,royalty_rate_usd,effective_rate_usd,gross_you_generated_usd,label_kept_usd,artist_earned_from_you_usd,plays_to_earn_1_dollar,global_streams_billions,global_gross_payout_m_usd,global_artist_earned_m_usd FROM finance.artist_revenue ORDER BY your_play_count DESC LIMIT 12").fetchall()
    d['artists'] = [dict(zip(['name','plays','watch_pct','rate','eff_rate','gross','label','artist','p_per_dollar','global_b','global_gross','global_artist'],r)) for r in rows]

    r = con.execute("SELECT ROUND(SUM(gross_you_generated_usd),5), ROUND(SUM(artist_earned_from_you_usd),5), SUM(your_play_count) FROM finance.artist_revenue").fetchone()
    d['your_total'] = {'gross':r[0],'artist':r[1],'plays':r[2]}

    rows = con.execute("SELECT platform,rate_min,rate_max,rate_mid,notes FROM finance.platform_benchmarks ORDER BY rate_mid DESC").fetchall()
    d['benchmarks'] = [dict(zip(['name','min','max','mid','notes'],r)) for r in rows]
    return d

def build(d):
    lq  = d['latest']
    yt  = d['your_total']
    gen = datetime.now().strftime("%B %d, %Y at %H:%M")
    top = d['artists'][0]['name'] if d['artists'] else 'Taylor Swift'
    top_artist_earned = d['artists'][0]['artist'] if d['artists'] else 0

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>YT Music Finance Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Playfair+Display:ital,wght@0,700;1,400&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{{
  --black:#07080a;--card:#111318;--border:#1a1d24;
  --red:#ff0000;--red2:rgba(255,0,0,.1);--red3:rgba(255,0,0,.05);
  --gold:#f5c842;--gold2:rgba(245,200,66,.1);
  --green:#00d084;--blue:#38bdf8;--purple:#a78bfa;
  --text:#f0ece4;--muted:#525660;--dim:#1e2128;
  --bebas:'Bebas Neue',sans-serif;--play:'Playfair Display',serif;--mono:'Space Mono',monospace;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{background:var(--black);color:var(--text);font-family:var(--mono);overflow-x:hidden;cursor:none}}
#cur{{width:8px;height:8px;background:var(--gold);border-radius:50%;position:fixed;pointer-events:none;z-index:9999;transform:translate(-50%,-50%);mix-blend-mode:difference}}
#ring{{width:30px;height:30px;border:1px solid rgba(245,200,66,.4);border-radius:50%;position:fixed;pointer-events:none;z-index:9998;transform:translate(-50%,-50%);transition:left .1s,top .1s}}
body::after{{content:'';position:fixed;inset:0;opacity:.4;pointer-events:none;z-index:9990;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.03'/%3E%3C/svg%3E")}}

.hero{{min-height:100vh;display:flex;flex-direction:column;justify-content:center;padding:64px;position:relative;overflow:hidden}}
.hero-bg{{position:absolute;inset:0;background:radial-gradient(ellipse 60% 55% at 85% 45%,rgba(255,0,0,.06) 0%,transparent 65%),radial-gradient(ellipse 40% 50% at 5% 85%,rgba(245,200,66,.04) 0%,transparent 60%)}}
.hero-chart-bg{{position:absolute;right:0;top:0;bottom:0;width:42%;opacity:.06;display:flex;align-items:flex-end;padding:40px;gap:3px}}
.hero-bar-d{{flex:1;background:var(--gold);border-radius:2px 2px 0 0}}

.live-badge{{display:inline-flex;align-items:center;gap:7px;background:rgba(245,200,66,.08);border:1px solid rgba(245,200,66,.2);border-radius:2px;padding:4px 12px;font-size:8px;letter-spacing:.15em;color:var(--gold);text-transform:uppercase;margin-bottom:16px;opacity:0;animation:up .6s .05s ease forwards}}
.live-dot{{width:5px;height:5px;border-radius:50%;background:var(--gold);animation:pulse 1.8s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
.eyebrow{{font-size:10px;letter-spacing:.22em;color:var(--gold);text-transform:uppercase;margin-bottom:16px;opacity:0;animation:up .6s .1s ease forwards}}
h1{{font-family:var(--bebas);font-size:clamp(66px,9vw,128px);line-height:.9;letter-spacing:.02em;opacity:0;animation:up .6s .2s ease forwards;max-width:700px}}
h1 .g{{color:var(--green)}} h1 .gld{{color:var(--gold)}} h1 .ghost{{-webkit-text-stroke:1px rgba(255,255,255,.1);color:transparent}}
.sub{{margin-top:20px;font-family:var(--play);font-style:italic;font-size:14px;color:var(--muted);max-width:460px;line-height:1.7;opacity:0;animation:up .6s .3s ease forwards}}
.hero-kpis{{display:flex;flex-wrap:wrap;gap:44px;margin-top:48px;opacity:0;animation:up .6s .4s ease forwards}}
.hkpi .v{{font-family:var(--bebas);font-size:46px;line-height:1;letter-spacing:.02em}}
.hkpi .l{{font-size:8px;letter-spacing:.16em;color:var(--muted);text-transform:uppercase;margin-top:3px}}
.v-gold{{color:var(--gold)}} .v-green{{color:var(--green)}} .v-blue{{color:var(--blue)}} .v-red{{color:var(--red)}}
.scroll-h{{margin-top:52px;font-size:9px;letter-spacing:.2em;color:var(--dim);text-transform:uppercase;opacity:0;animation:up .6s .6s ease forwards,blink 2s 1.5s infinite}}
@keyframes blink{{0%,100%{{opacity:.2}}50%{{opacity:.8}}}}
@keyframes up{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:none}}}}

.ticker{{background:#0e1014;border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:10px 0;overflow:hidden;white-space:nowrap}}
.ticker-inner{{display:inline-flex;gap:48px;animation:ticker 28s linear infinite}}
.ticker-item{{font-size:10px;letter-spacing:.06em;display:flex;align-items:center;gap:8px}}
.ticker-sym{{color:var(--gold);font-weight:700}}
@keyframes ticker{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}

.dash{{padding:0 44px 80px}}
.sec{{font-size:9px;letter-spacing:.26em;color:var(--gold);text-transform:uppercase;padding:34px 0 14px;border-top:1px solid var(--border);display:flex;align-items:center;gap:12px}}
.sec::after{{content:'';flex:1;height:1px;background:var(--border)}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:2px;margin-bottom:2px}}
.g3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:2px;margin-bottom:2px}}
.g4{{display:grid;grid-template-columns:repeat(4,1fr);gap:2px;margin-bottom:2px}}

.card{{background:var(--card);border:1px solid var(--border);padding:24px 26px;position:relative;overflow:hidden;transition:border-color .2s}}
.card:hover{{border-color:#2a2d38}}
.card::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--gold),transparent);opacity:0;transition:opacity .3s}}
.card:hover::before{{opacity:.3}}
.clbl{{font-size:8px;letter-spacing:.18em;color:var(--muted);text-transform:uppercase;margin-bottom:9px}}
.cval{{font-family:var(--bebas);font-size:48px;line-height:1;letter-spacing:.02em}}
.cunit{{font-size:10px;margin-top:3px}}
.cdelta{{position:absolute;top:22px;right:22px;font-size:9px;padding:2px 7px;border-radius:2px}}
.up{{color:var(--green);background:rgba(0,208,132,.1)}}
.dn{{color:#ff4d6d;background:rgba(255,77,109,.1)}}
.neu{{color:var(--gold);background:rgba(245,200,66,.1)}}

.cc{{background:var(--card);border:1px solid var(--border);padding:26px 30px;margin-bottom:2px}}
.ctitle{{font-family:var(--play);font-size:16px;font-weight:700;margin-bottom:3px}}
.csub{{font-size:8px;color:var(--muted);letter-spacing:.1em;text-transform:uppercase;margin-bottom:22px}}

.lc{{position:relative;height:150px;margin-top:8px}}
.lc svg{{width:100%;height:100%;overflow:visible}}
.xlbls{{display:flex;justify-content:space-between;margin-top:6px}}
.xlbl{{font-size:7px;color:var(--muted)}}

.bchart{{display:flex;flex-direction:column;gap:9px}}
.brow{{display:grid;grid-template-columns:130px 1fr 64px;align-items:center;gap:12px}}
.blbl{{font-size:10px;color:var(--text);text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.btrack{{height:4px;background:var(--dim);overflow:hidden}}
.bfill{{height:100%;transform-origin:left;transform:scaleX(0);animation:grow 1s cubic-bezier(.16,1,.3,1) both}}
@keyframes grow{{to{{transform:scaleX(1)}}}}
.bval{{font-size:9px;text-align:right}}

.agrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:2px;margin-bottom:2px}}
.acard{{background:var(--card);border:1px solid var(--border);padding:18px 20px;transition:all .2s;position:relative;overflow:hidden}}
.acard:hover{{border-color:#2a2d38;transform:translateY(-2px)}}
.acard::after{{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;transform:scaleX(0);transition:transform .3s;transform-origin:left}}
.acard:hover::after{{transform:scaleX(1)}}
.arank{{font-family:var(--bebas);font-size:36px;color:var(--dim);line-height:1;margin-bottom:4px}}
.aname{{font-size:12px;font-weight:700;margin-bottom:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.astat{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px;padding-bottom:5px;border-bottom:1px solid var(--border)}}
.astat:last-child{{border-bottom:none;margin-bottom:0;padding-bottom:0}}
.astat-lbl{{font-size:8px;color:var(--muted);letter-spacing:.08em;text-transform:uppercase}}
.astat-val{{font-family:var(--bebas);font-size:16px}}

.bench-row{{display:flex;align-items:center;gap:14px;padding:11px 0;border-bottom:1px solid var(--border)}}
.bench-name{{font-size:11px;font-weight:700;width:120px;flex-shrink:0}}
.bench-bw{{flex:1;height:5px;background:var(--dim);overflow:hidden}}
.bench-bf{{height:100%;transform-origin:left;transform:scaleX(0);animation:grow 1s cubic-bezier(.16,1,.3,1) both}}
.bench-rate{{font-family:var(--bebas);font-size:18px;width:60px;text-align:right}}
.bench-note{{font-size:8px;color:var(--muted);width:220px;flex-shrink:0}}

.insight{{background:linear-gradient(135deg,rgba(245,200,66,.06),transparent);border:1px solid rgba(245,200,66,.18);border-left:3px solid var(--gold);padding:22px 26px;margin-bottom:2px}}
.insight.green{{background:linear-gradient(135deg,rgba(0,208,132,.06),transparent);border-color:rgba(0,208,132,.18);border-left-color:var(--green)}}
.itag{{font-size:8px;letter-spacing:.2em;text-transform:uppercase;margin-bottom:8px}}
.itext{{font-family:var(--play);font-style:italic;font-size:15px;line-height:1.6;color:var(--text);max-width:700px}}

.footer{{border-top:1px solid var(--border);padding:22px 44px;display:flex;justify-content:space-between;align-items:center;font-size:8px;letter-spacing:.13em;color:var(--muted);text-transform:uppercase}}
.footer .logo{{font-family:var(--bebas);font-size:17px;color:var(--gold);letter-spacing:.1em}}
.rv{{opacity:0;transform:translateY(18px);transition:opacity .5s ease,transform .5s ease}}
.rv.on{{opacity:1;transform:none}}
</style>
</head>
<body>
<div id="cur"></div><div id="ring"></div>

<div class="ticker"><div class="ticker-inner" id="ticker"></div></div>

<section class="hero">
  <div class="hero-bg"></div>
  <div class="hero-chart-bg" id="heroBars"></div>
  <div class="live-badge"><span class="live-dot"></span>Live from DuckDB · {gen}</div>
  <div class="eyebrow">YouTube Music · Finance Intelligence · Option 1 + 2</div>
  <h1>MONEY<br><span class="gld">BEHIND</span><br><span class="ghost">THE MUSIC</span></h1>
  <p class="sub">YouTube's $9.7B quarterly ad revenue decoded. Your personal contribution to artist royalties calculated. Google financials + personal data in one warehouse.</p>
  <div class="hero-kpis">
    <div class="hkpi"><div class="v v-gold" id="h1">0</div><div class="l">YT Ad Rev Q4'24 ($M)</div></div>
    <div class="hkpi"><div class="v v-green" id="h2">0</div><div class="l">Alphabet Op Margin %</div></div>
    <div class="hkpi"><div class="v v-blue" id="h3">0</div><div class="l">YT Premium Subs (M)</div></div>
    <div class="hkpi"><div class="v v-gold" id="h4">0</div><div class="l">GOOGL Price $</div></div>
  </div>
  <div class="scroll-h">↓ &nbsp; Scroll to explore</div>
</section>

<div class="dash">

<div class="sec rv">01 — YouTube Business Financials</div>
<div class="g4 rv">
  <div class="card">
    <div class="clbl">YT Ad Revenue Q4'24</div>
    <div class="cval" style="color:var(--gold)">${lq['yt_rev']:,}M</div>
    <div class="cunit" style="color:var(--gold)">USD quarterly</div>
    <div class="cdelta up">↑ {lq['yoy'] or 5.4}% YoY</div>
  </div>
  <div class="card">
    <div class="clbl">Alphabet Op Margin</div>
    <div class="cval" style="color:var(--green)">{lq['op_margin']}<span style="font-size:24px">%</span></div>
    <div class="cunit" style="color:var(--green)">record high</div>
    <div class="cdelta up">↑ was 23.7% in 2022</div>
  </div>
  <div class="card">
    <div class="clbl">YT Share of Alphabet</div>
    <div class="cval" style="color:var(--blue)">{round(lq['yt_rev']/lq['alpha_rev']*100,1)}<span style="font-size:24px">%</span></div>
    <div class="cunit" style="color:var(--blue)">of Google total revenue</div>
    <div class="cdelta neu">→ stable</div>
  </div>
  <div class="card">
    <div class="clbl">Alphabet Q4'24 Revenue</div>
    <div class="cval" style="color:var(--text)">${lq['alpha_rev']:,}M</div>
    <div class="cunit" style="color:var(--muted)">total Google revenue</div>
    <div class="cdelta up">↑ record quarter</div>
  </div>
</div>

<div class="g2 rv">
  <div class="cc">
    <div class="ctitle">YouTube Ad Revenue</div>
    <div class="csub">USD millions · 2022–2024 · quarterly</div>
    <div class="lc" id="revChart"></div>
    <div class="xlbls" id="revLbls"></div>
  </div>
  <div class="cc">
    <div class="ctitle">Alphabet Operating Margin</div>
    <div class="csub">% operating margin · expanding consistently</div>
    <div class="lc" id="marginChart"></div>
    <div class="xlbls" id="marginLbls"></div>
  </div>
</div>

<div class="cc rv">
  <div class="ctitle">GOOGL Stock Price</div>
  <div class="csub">USD monthly close · 2022–2024 · +123% from Dec 2022 low</div>
  <div class="lc" id="stockChart"></div>
  <div class="xlbls" id="stockLbls"></div>
</div>

<div class="insight rv">
  <div class="itag" style="color:var(--gold)">⬡ Business Insight</div>
  <div class="itext">YouTube's ad revenue grew from <strong>$6.9B in Q1 2022 to $9.7B in Q4 2024</strong> — a 41% increase — while Alphabet's operating margin expanded from 23.7% to 32.1%. Every stream you make on YouTube Music contributes to the ad inventory that powers this growth. GOOGL stock recovered <strong>+123%</strong> from its December 2022 low of $88.</div>
</div>

<div class="sec rv">02 — Artist Revenue Estimator</div>
<div class="g3 rv">
  <div class="card">
    <div class="clbl">Total You Generated</div>
    <div class="cval" style="color:var(--gold)">${yt['gross']}</div>
    <div class="cunit" style="color:var(--gold)">gross from {int(yt['plays']):,} plays</div>
    <div class="cdelta neu">to rights holders</div>
  </div>
  <div class="card">
    <div class="clbl">Artists Actually Earned</div>
    <div class="cval" style="color:var(--green)">${yt['artist']}</div>
    <div class="cunit" style="color:var(--green)">after label's ~75% cut</div>
    <div class="cdelta dn">label keeps the rest</div>
  </div>
  <div class="card">
    <div class="clbl">Your Top Channel</div>
    <div class="cval" style="font-size:26px;color:var(--text);margin-top:6px">{top}</div>
    <div class="cunit" style="color:var(--muted);margin-top:6px">most watched by you</div>
  </div>
</div>

<div class="agrid rv" id="artistCards"></div>

<div class="insight green rv">
  <div class="itag" style="color:var(--green)">⬡ Revenue Insight</div>
  <div class="itext">{top} earned approximately <strong>${top_artist_earned:.5f} from your {d['artists'][0]['plays']} personal plays</strong> on YouTube Music. Their effective per-play rate is adjusted for your {d['artists'][0]['watch_pct']}% average watch percentage — partial plays earn proportionally less. Globally, their estimated <strong>{d['artists'][0]['global_b']}B YouTube streams</strong> generated around <strong>${d['artists'][0]['global_artist']}M directly</strong> for the artist after label cuts.</div>
</div>

<div class="sec rv">03 — Platform Royalty Benchmarks</div>
<div class="cc rv">
  <div class="ctitle">Per-Stream Payout Comparison</div>
  <div class="csub">USD royalty rate across major platforms — YouTube Music pays least, reaches most</div>
  <div id="benchmarks"></div>
</div>

<div class="insight rv">
  <div class="itag" style="color:var(--gold)">⬡ Platform Insight</div>
  <div class="itext">YouTube Music pays <strong>$0.001–$0.002 per stream</strong> — the lowest of all major platforms. But with <strong>2 billion+ monthly users</strong>, total royalty volume can still be substantial for viral artists. An independent artist needs <strong>~667 YouTube Music plays to earn $1</strong> versus only 222 plays on Tidal. Scale vs rate — the core tension in music streaming economics.</div>
</div>

</div>

<div class="footer">
  <div class="logo">YT Music Finance</div>
  <div>Option 1 + 2 · DuckDB + dbt · {gen}</div>
  <div>Sources: Alphabet SEC Filings · IFPI 2024 · Industry Studies</div>
</div>

<script>
const QUARTERLY={json.dumps(d['quarterly'])};
const STOCK={json.dumps(d['stock'])};
const ARTISTS={json.dumps(d['artists'])};
const BENCHMARKS={json.dumps(d['benchmarks'])};

const cur=document.getElementById('cur'),ring=document.getElementById('ring');
let mx=0,my=0,rx=0,ry=0;
document.addEventListener('mousemove',e=>{{mx=e.clientX;my=e.clientY;cur.style.left=mx+'px';cur.style.top=my+'px'}});
setInterval(()=>{{rx+=(mx-rx)*.13;ry+=(my-ry)*.13;ring.style.left=rx+'px';ring.style.top=ry+'px'}},14);

function count(el,to,dur=1600,dec=0){{
  let s=null;
  (function step(ts){{if(!s)s=ts;const p=Math.min((ts-s)/dur,1),e=1-Math.pow(1-p,4);
  el.textContent=dec>0?(e*to).toFixed(dec):Math.round(e*to);if(p<1)requestAnimationFrame(step)}})(performance.now());
}}
setTimeout(()=>{{
  count(document.getElementById('h1'),{lq['yt_rev']});
  count(document.getElementById('h2'),{lq['op_margin']},1600,1);
  count(document.getElementById('h3'),120);
  count(document.getElementById('h4'),196);
}},500);

// Ticker
const td=[['GOOGL','$196','Dec 2024'],['YT REV','$9.7B','Q4 2024'],['OP MAR','{lq["op_margin"]}%','record'],['YT SUBS','120M','premium'],['GROWTH','+41%','2yr'],['ARTISTS','{len(d["artists"])}','tracked'],['GOOGL','$196','Dec 2024'],['YT REV','$9.7B','Q4 2024']];
const tk=document.getElementById('ticker');
[...td,...td].forEach(([s,v,c])=>{{tk.innerHTML+=`<div class="ticker-item"><span class="ticker-sym">${{s}}</span><span style="color:var(--text)">${{v}}</span><span style="color:var(--gold);font-size:9px">${{c}}</span></div>`}});

// Hero bars
const hb=document.getElementById('heroBars');
QUARTERLY.forEach(q=>{{const d=document.createElement('div');d.className='hero-bar-d';d.style.height=(q.yt_rev/9700*80)+'%';hb.appendChild(d)}});

// SVG line chart
function makeLine(cId,lId,datasets,ylabStep=3){{
  const container=document.getElementById(cId);if(!container)return;
  const W=container.offsetWidth||600,H=150;
  const pad={{t:10,r:10,b:10,l:44}};
  const cw=W-pad.l-pad.r,ch=H-pad.t-pad.b;
  const allV=datasets.flatMap(ds=>ds.vals);
  const minV=Math.min(...allV)*.94,maxV=Math.max(...allV)*1.03;
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width','100%');svg.setAttribute('height',H);svg.setAttribute('viewBox',`0 0 ${{W}} ${{H}}`);
  [0,.25,.5,.75,1].forEach(p=>{{
    const y=pad.t+ch*(1-p),v=Math.round(minV+(maxV-minV)*p);
    const l=document.createElementNS('http://www.w3.org/2000/svg','line');
    l.setAttribute('x1',pad.l);l.setAttribute('x2',pad.l+cw);l.setAttribute('y1',y);l.setAttribute('y2',y);
    l.setAttribute('stroke','#1e2028');l.setAttribute('stroke-width','1');svg.appendChild(l);
    const t=document.createElementNS('http://www.w3.org/2000/svg','text');
    t.setAttribute('x',pad.l-4);t.setAttribute('y',y+4);t.setAttribute('text-anchor','end');
    t.setAttribute('fill','#525660');t.setAttribute('font-size','8');t.setAttribute('font-family','Space Mono,monospace');
    t.textContent=v>=1000?(v/1000).toFixed(1)+'k':v;svg.appendChild(t);
  }});
  datasets.forEach((ds,di)=>{{
    const n=ds.vals.length;
    const pts=ds.vals.map((v,i)=>{{const x=pad.l+cw*(i/(n-1));const y=pad.t+ch*(1-(v-minV)/(maxV-minV));return [x,y]}});
    const pD='M'+pts.map(p=>p.join(',')).join(' L');
    const area=document.createElementNS('http://www.w3.org/2000/svg','path');
    area.setAttribute('d',pD+` L${{pts[pts.length-1][0]}},${{pad.t+ch}} L${{pts[0][0]}},${{pad.t+ch}} Z`);
    area.setAttribute('fill',ds.color);area.setAttribute('opacity','.1');svg.appendChild(area);
    const path=document.createElementNS('http://www.w3.org/2000/svg','path');
    path.setAttribute('d',pD);path.setAttribute('fill','none');path.setAttribute('stroke',ds.color);
    path.setAttribute('stroke-width','2');path.setAttribute('stroke-linecap','round');
    const len=2000;path.style.strokeDasharray=len;path.style.strokeDashoffset=len;
    path.style.transition='stroke-dashoffset 1.4s cubic-bezier(.16,1,.3,1)';
    svg.appendChild(path);setTimeout(()=>path.style.strokeDashoffset='0',200);
    const lp=pts[pts.length-1];
    const dot=document.createElementNS('http://www.w3.org/2000/svg','circle');
    dot.setAttribute('cx',lp[0]);dot.setAttribute('cy',lp[1]);dot.setAttribute('r','3');
    dot.setAttribute('fill',ds.color);dot.setAttribute('stroke','#07080a');dot.setAttribute('stroke-width','2');
    svg.appendChild(dot);
  }});
  container.appendChild(svg);
  const lc=document.getElementById(lId);if(!lc)return;
  const labels=datasets[0].labels||[];
  labels.forEach((l,i)=>{{const s=document.createElement('span');s.className='xlbl';s.textContent=i%3===0?l:'';lc.appendChild(s)}});
}}

const qLabels=QUARTERLY.map(q=>q.yq);
makeLine('revChart','revLbls',[{{vals:QUARTERLY.map(q=>q.yt_rev),color:'#f5c842',labels:qLabels}}]);
makeLine('marginChart','marginLbls',[{{vals:QUARTERLY.map(q=>q.op_margin),color:'#00d084',labels:qLabels}}]);
const stkLabels=STOCK.map(s=>s.ym.slice(2));
makeLine('stockChart','stockLbls',[{{vals:STOCK.map(s=>s.price),color:'#f5c842',labels:stkLabels}}]);

// Artist cards
const ACOLS=['#f5c842','#00d084','#38bdf8','#a78bfa','#ff4d6d','#f5c842','#00d084','#38bdf8','#a78bfa','#ff4d6d','#f5c842','#00d084'];
const ag=document.getElementById('artistCards');
ARTISTS.forEach((a,i)=>{{
  const col=ACOLS[i]||'#f5c842';
  ag.innerHTML+=`<div class="acard" style="border-color:var(--border)">
    <style>.agrid .acard:nth-child(${{i+1}})::after{{background:${{col}}}}</style>
    <div class="arank" style="color:rgba(255,255,255,.05)">${{String(i+1).padStart(2,'0')}}</div>
    <div class="aname" style="color:${{col}}">${{a.name}}</div>
    <div class="astat"><span class="astat-lbl">Your Plays</span><span class="astat-val" style="color:var(--text)">${{a.plays}}</span></div>
    <div class="astat"><span class="astat-lbl">Avg Watch %</span><span class="astat-val" style="color:var(--muted);font-size:14px">${{a.watch_pct}}%</span></div>
    <div class="astat"><span class="astat-lbl">Artist Earned</span><span class="astat-val" style="color:${{col}}">$${{a.artist?.toFixed(5)||'—'}}</span></div>
    <div class="astat"><span class="astat-lbl">Global Career</span><span class="astat-val" style="color:var(--muted);font-size:13px">${{a.global_artist!==null?'$'+a.global_artist+'M':'—'}}</span></div>
  </div>`;
}});

// Benchmarks
const bEl=document.getElementById('benchmarks');
const maxR=Math.max(...BENCHMARKS.map(b=>b.mid));
BENCHMARKS.forEach((b,i)=>{{
  const isYT=b.name.includes('YouTube');const col=isYT?'#ff4d6d':b.name==='Tidal'?'#00d084':'#525660';
  bEl.innerHTML+=`<div class="bench-row">
    <div class="bench-name" style="color:${{isYT?'#ff4d6d':'var(--text)'}}">${{b.name}}</div>
    <div class="bench-bw"><div class="bench-bf" style="background:${{col}};animation-delay:${{i*.08}}s;width:${{b.mid/maxR*100}}%"></div></div>
    <div class="bench-rate" style="color:${{col}}">$${{b.mid}}</div>
    <div class="bench-note">${{b.notes}}</div>
  </div>`;
}});

const rvs=document.querySelectorAll('.rv');
const obs=new IntersectionObserver(e=>e.forEach(x=>{{if(x.isIntersecting)x.target.classList.add('on')}}),{{threshold:.07}});
rvs.forEach(r=>obs.observe(r));
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("💰 YT Music Finance Dashboard Generator")
    print("=" * 40)
    if not os.path.exists(DB_PATH):
        print("❌ Run pipeline first"); raise SystemExit(1)
    con = duckdb.connect(DB_PATH, read_only=True)
    tables = con.execute("SHOW ALL TABLES").df()
    if 'finance' not in tables['schema'].values:
        con.close(); print("❌ Run: python load_yt_finance.py"); raise SystemExit(1)
    print("\n→ Querying DuckDB...")
    d = fetch(con); con.close()
    print(f"  YT Q4 Rev: ${d['latest']['yt_rev']:,}M | Artists: {len(d['artists'])}")
    print("\n→ Building finance dashboard...")
    html = build(d)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT,"w",encoding="utf-8") as f: f.write(html)
    print(f"\n✅ Saved → {OUTPUT}\n")
