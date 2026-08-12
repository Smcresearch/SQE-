"""
Generate factsheet.html for SQE (SMC Quant Equity) portfolio.
Reads data.js for live metrics and holdings. Embeds SMC logo.
"""
import json, base64, re, subprocess, tempfile
from datetime import datetime
from pathlib import Path

# ── Logo ──
import shutil, os
logo_src_path = r'C:/Users/PC2546/Desktop/SMCNEWLOGO.webp'
logo_dst_path = r'd:/SQE-host/smc_logo.webp'
if os.path.exists(logo_src_path):
    shutil.copy2(logo_src_path, logo_dst_path)
logo_src = 'smc_logo.webp'

# ── Load data.js ──
with open(r'd:/SQE-host/data.js', 'r', encoding='utf-8') as f:
    content = f.read()

# remove 'const DASHBOARD_DATA = ' at start and '; \n' at end to make it JSON
clean = content.strip()
if clean.startswith('const DASHBOARD_DATA ='):
    clean = clean[len('const DASHBOARD_DATA ='):].strip()
if clean.endswith(';'):
    clean = clean[:-1].strip()

data = json.loads(clean)

# Use total759 (All Indices) by default (contains 30 stocks)
portfolio = data['total759']['current_portfolio']
base_metrics = data['total759']['layer_metrics']['Base']
exec_sum = data['total759']['exec_summary']

# Last update
last_update = data.get('last_update', 'N/A')
try:
    dt = datetime.strptime(last_update[:10], '%Y-%m-%d')
    last_update_fmt = dt.strftime('%B %d, %Y')
except:
    last_update_fmt = last_update

# Metrics
M = {
    'CAGR': base_metrics['CAGR'],
    # total759/nifty500 'Bench' series is the Nifty 500; the Nifty 50 lives in the
    # nifty50 universe's own 'Bench' (app.js injects it as 'BenchN50').
    'Bench_CAGR': exec_sum['CAGR']['Bench'] * 100,
    'Bench_N50_CAGR': data['nifty50']['exec_summary']['CAGR']['Bench'] * 100,
    # Alpha = portfolio CAGR - benchmark CAGR, consistent with how it is defined below.
    'Alpha': exec_sum['Alpha vs Bench']['Base'] * 100,
    'Volatility': base_metrics['Volatility'],
    'Sharpe': base_metrics['Sharpe'],
    'Sortino': base_metrics['Sortino'],
    'Calmar': base_metrics['Calmar'],
    'Max_DD': base_metrics['Max_DD'],
    'Win_Rate': base_metrics['Win_Rate'],
    'Avg_Gain': base_metrics['Avg_Gain'],
    'Avg_Loss': base_metrics['Avg_Loss'],
    'Total_Return': base_metrics['Total_Return'],
    'Best_Month': exec_sum['Best Month']['Base'] * 100,
    'Worst_Month': exec_sum['Worst Month']['Base'] * 100,
    'VaR_95': exec_sum['VaR 95%']['Base'] * 100,
}

# Sector weights
sector_map = {}
for h in portfolio:
    s = h['sector']
    sector_map[s] = sector_map.get(s, 0) + h['weight'] * 100
sector_map = dict(sorted(sector_map.items(), key=lambda x: -x[1]))

sector_colors = [
    '#1a73e8','#34a853','#fbbc04','#ea4335','#9c27b0',
    '#00bcd4','#ff5722','#607d8b','#795548','#e91e63',
]
sector_rows = ''
for idx_s, (sec, wt) in enumerate(sector_map.items()):
    c = sector_colors[idx_s % len(sector_colors)]
    sector_rows += f'''<div class="alloc-row"><span class="alloc-name">{sec}</span><div class="alloc-track"><div class="alloc-fill" style="width:{wt:.1f}%;background:{c}"></div></div><span class="alloc-pct">{wt:.1f}%</span></div>\n'''

holdings_rows = ''
for idx_h, h in enumerate(portfolio, 1):
    sym = h['clean_symbol']
    wt = h['weight'] * 100
    sec = h['sector']
    ltp = h.get('ltp', 0)
    chg = h.get('change_pct', 0)
    cls = 'g' if chg >= 0 else 'r'
    chg_s = f"+{chg:.2f}%" if chg >= 0 else f"{chg:.2f}%"
    badge = ' <span class="badge-new">NEW</span>' if h.get('status') == 'Added' else ''
    holdings_rows += f'<tr><td class="c">{idx_h}</td><td class="sym">{sym}{badge}</td><td>{sec}</td><td class="mono b">{wt:.1f}%</td><td class="mono">₹{ltp:,.2f}</td><td class="{cls} mono">{chg_s}</td></tr>\n'

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SMC SQE SmallCase — Factsheet</title>
<meta name="description" content="Official factsheet for the SMC Quant Equity (SQE) SmallCase portfolio.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Roboto+Mono:wght@400;500&display=swap">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --pri:#0f2b54;--pri2:#1565c0;--acc:#16c784;--red:#ea3943;
  --bg:#f3f6fb;--bdr:#dde3ef;--txt:#1a1a2e;--sub:#6b7a99;--wh:#fff;
  --sh:0 2px 16px rgba(15,43,84,.08);--r:12px;
  --f:'Inter',system-ui,sans-serif;--m:'Roboto Mono',monospace;
}}
html{{scroll-behavior:smooth}}
body{{font-family:var(--f);background:var(--bg);color:var(--txt);font-size:13px;line-height:1.65;-webkit-font-smoothing:antialiased}}
@page{{size:A4;margin:10mm 9mm 12mm}}
@media print{{
  /* Chrome strips background colours when printing unless told otherwise —
     without this the blue header, sector bars and metric colours all render white. */
  *{{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}}
  html,body{{background:#fff;font-size:9.5px}}
  .no-print{{display:none!important}}
  .wrap{{max-width:none;padding:0}}
  .brk{{page-break-before:always}}
  .card{{box-shadow:none;margin-bottom:0;border:none;border-radius:0;overflow:visible}}
  /* Keep small units intact, but let tall cards/sections flow across pages. */
  .sec{{break-inside:auto;padding:14px 22px}}
  .sec-t{{break-after:avoid}}
  .ic,.ri,.mr,.rc,.sb{{break-inside:avoid}}
  .rat{{break-inside:avoid}}
  table{{break-inside:auto;font-size:8.6px!important}}
  thead{{display:table-header-group}}
  tr{{break-inside:avoid;break-after:auto}}
  /* Tighten rows so all 30 holdings fit on a single page instead of
     spilling a handful onto a near-empty one. !important is required:
     the base table rules are declared later in this stylesheet and would
     otherwise win on equal specificity. */
  thead th,td{{padding:4.1px 8px!important;font-size:8.6px!important}}
  tr:hover td{{background:transparent!important}}
  .hdr{{padding:20px 30px 22px}}
  .disc{{break-inside:auto}}
  a{{text-decoration:none;color:inherit}}
}}
.wrap{{max-width:880px;margin:0 auto;padding:20px 16px 80px}}
.card{{background:var(--wh);border-radius:var(--r);box-shadow:var(--sh);margin-bottom:20px;overflow:hidden}}

/* ─── HEADER ─── */
.hdr-logo-bar{{background:#ffffff;padding:20px 40px;text-align:center;border-bottom:1px solid var(--bdr);display:flex;justify-content:center;align-items:center}}
.logo{{display:block;height:45px;max-width:100%;object-fit:contain}}
.hdr{{background:linear-gradient(135deg,#0f2b54 0%,#1565c0 60%,#1e88e5 100%);color:#fff;padding:28px 40px 30px;text-align:center;position:relative}}
.hdr::after{{content:'';position:absolute;inset:0;background:url("data:image/svg+xml,%3Csvg width='60' height='60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 30h60M30 0v60' stroke='%23fff' stroke-opacity='.03' stroke-width='1'/%3E%3C/svg%3E");pointer-events:none}}
.hdr>*{{position:relative;z-index:1}}
.tag{{display:inline-block;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:3px 14px;font-size:10px;font-weight:700;letter-spacing:1.8px;text-transform:uppercase;margin-bottom:14px}}
.hdr h1{{font-size:24px;font-weight:800;letter-spacing:-.4px;margin-bottom:6px}}
.hdr .sub{{font-size:12.5px;opacity:.75;margin-bottom:22px}}
.pills{{display:flex;justify-content:center;gap:28px;flex-wrap:wrap}}
.pill{{text-align:center}}
.pill .v{{font-size:22px;font-weight:800}}
.pill .v.green{{color:#4ade80}}
.pill .l{{font-size:10px;opacity:.65;margin-top:2px}}
.pill .chip{{display:inline-block;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.22);border-radius:16px;padding:3px 12px;font-size:10.5px;font-weight:600}}
.hdr .ts{{margin-top:18px;font-size:10px;opacity:.5}}
.hdr .ts a{{color:rgba(255,255,255,.85);text-decoration:none}}

/* ─── SECTION ─── */
.sec{{padding:24px 32px;border-bottom:1px solid var(--bdr)}}
.sec:last-child{{border-bottom:none}}
.sec-t{{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;color:var(--pri);margin-bottom:16px;display:flex;align-items:center;gap:8px}}
.sec-t::after{{content:'';flex:1;height:1px;background:var(--bdr)}}

/* ─── INFO GRID ─── */
.ig{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px}}
.ic{{background:var(--bg);border:1px solid var(--bdr);border-radius:8px;padding:12px 14px}}
.ic .k{{font-size:10px;color:var(--sub);font-weight:600;text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px}}
.ic .v{{font-size:14px;font-weight:700}}
.ic .v.g{{color:var(--acc)}} .ic .v.b{{color:var(--pri2)}} .ic .v.r{{color:var(--red)}}

/* ─── RATIONALE ─── */
.rat{{background:linear-gradient(135deg,#f0f5ff 0%,#e8f5e9 100%);border:1px solid #c8d8f0;border-left:4px solid var(--pri2);border-radius:8px;padding:18px 22px;font-size:13px;line-height:1.8;color:var(--txt)}}
.rat strong{{color:var(--pri)}}
.rat ul{{margin:10px 0 0 20px}}
.rat li{{margin-bottom:6px}}

/* ─── REBALANCE ─── */
.reb{{display:flex;gap:14px;flex-wrap:wrap}}
.ri{{flex:1;min-width:130px;background:var(--bg);border:1px solid var(--bdr);border-radius:8px;padding:14px;text-align:center}}
.ri .k{{font-size:10px;color:var(--sub);font-weight:600;text-transform:uppercase;letter-spacing:.4px}}
.ri .v{{font-size:14px;font-weight:700;color:var(--pri);margin-top:4px}}

/* ─── METRICS ─── */
.mg{{display:grid;grid-template-columns:1fr 1fr;gap:28px}}
@media(max-width:600px){{.mg{{grid-template-columns:1fr}}}}
.mr{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--bdr)}}
.mr:last-child{{border-bottom:none}}
.mr .k{{font-size:12px;color:var(--sub)}}
.mr .v{{font-size:13px;font-weight:700;font-family:var(--m)}}
.g{{color:var(--acc)!important}} .r{{color:var(--red)!important}} .n{{color:var(--txt)}}

/* ─── ALLOCATION ─── */
.alloc-row{{display:flex;align-items:center;gap:10px;padding:6px 0}}
.alloc-name{{font-size:11.5px;min-width:210px;color:var(--txt)}}
.alloc-track{{flex:1;background:var(--bg);border-radius:4px;height:7px;overflow:hidden}}
.alloc-fill{{height:100%;border-radius:4px}}
.alloc-pct{{font-size:12px;font-weight:700;font-family:var(--m);min-width:42px;text-align:right}}

/* ─── TABLE ─── */
table{{width:100%;border-collapse:collapse;font-size:12px}}
thead th{{background:var(--pri);color:#fff;padding:9px 10px;text-align:left;font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
thead th:first-child{{border-radius:6px 0 0 0}} thead th:last-child{{border-radius:0 6px 0 0}}
td{{padding:9px 10px;border-bottom:1px solid var(--bdr)}}
tr:last-child td{{border-bottom:none}}
tr:nth-child(even) td{{background:#fafbfd}}
tr:hover td{{background:#f0f4ff}}
.c{{text-align:center;color:var(--sub);font-size:11px}}
.sym{{font-weight:700;font-size:13px;color:var(--pri)}}
.b{{font-weight:700}}
.mono{{font-family:var(--m)}}
.badge-new{{display:inline-block;background:#e3f2fd;color:#1565c0;font-size:8px;font-weight:800;border-radius:3px;padding:1px 5px;margin-left:4px;vertical-align:middle;letter-spacing:.3px}}

/* ─── RISK CARDS ─── */
.rg{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
@media(max-width:600px){{.rg{{grid-template-columns:1fr}}}}
.rc{{background:var(--bg);border:1px solid var(--bdr);border-radius:8px;padding:14px 16px}}
.rc .rk{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--red);margin-bottom:5px}}
.rc p{{font-size:11px;color:var(--sub);line-height:1.6}}

/* ─── DISCLAIMER ─── */
.disc{{background:#f9fafc;border:1px solid var(--bdr);border-radius:8px;padding:16px 20px;font-size:10px;color:var(--sub);line-height:1.75}}
.disc strong{{color:var(--red)}}

/* ─── FOOTER ─── */
.ft{{background:var(--pri);color:rgba(255,255,255,.65);text-align:center;padding:18px 32px;font-size:10.5px;border-radius:var(--r)}}
.ft strong{{color:#fff}} .ft a{{color:rgba(255,255,255,.85);text-decoration:none}}

/* ─── PRINT BTN ─── */
.pbtn{{position:fixed;bottom:20px;right:20px;background:var(--pri2);color:#fff;border:none;border-radius:50px;padding:11px 22px;font-size:12px;font-weight:600;cursor:pointer;box-shadow:0 4px 16px rgba(21,101,192,.35);font-family:var(--f);z-index:999;transition:transform .2s}}
.pbtn:hover{{transform:translateY(-2px)}}

@media(max-width:600px){{
  .sec{{padding:18px 16px}}
  .hdr{{padding:24px 18px 22px}}
  .alloc-name{{min-width:140px}}
  .rg,.ig{{grid-template-columns:1fr}}
}}
</style>
</head>
<body>
<div class="wrap">

<!-- ═══════════ PAGE 1 ═══════════ -->
<div class="card">

  <!-- HEADER LOGO BAR -->
  <div class="hdr-logo-bar">
    <img class="logo" src="{logo_src}" alt="SMC Research">
  </div>

  <!-- HEADER -->
  <div class="hdr">
    <div class="tag">Factsheet</div>
    <h1>SQE SmallCase Terminal</h1>
    <p class="sub">SMC Quant Equity — All Indices Portfolio</p>
    <div class="pills">
      <div class="pill"><div class="v green">{M['CAGR']:.2f}%</div><div class="l">CAGR</div></div>
      <div class="pill"><div class="v green">{M['Total_Return']:.1f}%</div><div class="l">Total Return</div></div>
      <div class="pill"><div class="chip">High Volatility</div><div class="l" style="margin-top:4px">Risk Level</div></div>
      <div class="pill"><div class="chip">Long Term</div><div class="l" style="margin-top:4px">Horizon</div></div>
    </div>
    <p class="ts">Last updated: {last_update_fmt} &nbsp;·&nbsp; <a href="https://smcresearch.github.io/SQE-/">View Live Dashboard →</a></p>
  </div>

  <!-- OVERVIEW -->
  <div class="sec">
    <div class="sec-t">Portfolio Overview</div>
    <div class="ig">
      <div class="ic"><div class="k">Portfolio Type</div><div class="v">Thematic / Quant</div></div>
      <div class="ic"><div class="k">Constituents</div><div class="v">Indian Stocks (NSE)</div></div>
      <div class="ic"><div class="k">Asset Class</div><div class="v">Equity Multi Cap</div></div>
      <div class="ic"><div class="k">Universe</div><div class="v">All NSE Indices</div></div>
      <div class="ic"><div class="k">No. of Stocks</div><div class="v b">{len(portfolio)}</div></div>
      <div class="ic"><div class="k">Launch Period</div><div class="v">January 2020</div></div>
      <div class="ic"><div class="k">CAGR (Portfolio)</div><div class="v g">{M['CAGR']:.2f}%</div></div>
      <div class="ic"><div class="k">CAGR (Nifty 500)</div><div class="v b">{M['Bench_CAGR']:.2f}%</div></div>
    </div>
  </div>

  <!-- RATIONALE -->
  <div class="sec">
    <div class="sec-t">Portfolio Rationale</div>
    <div class="rat">
      <strong>SQE (SMC Quant Equity)</strong> is a concentrated, research-backed equity portfolio
      designed for <strong>long-term wealth creation</strong>. It aims to deliver superior
      risk-adjusted returns by investing in a select basket of high-quality Indian stocks
      across all major NSE indices.
      <ul>
        <li>Stocks are selected using a <strong>proprietary quantitative model</strong> developed
        by SMC Research that evaluates each stock's risk-return profile relative to the
        broader market</li>
        <li>The portfolio holds <strong>{len(portfolio)} high-conviction positions</strong> drawn from
        the full universe of NSE-listed companies — large, mid and small cap — with individual
        position sizes capped at <strong>10%</strong> to control single-stock risk</li>
        <li>Every month, the portfolio is <strong>systematically rebalanced</strong> to capture
        new opportunities and manage risk — there is no discretionary or emotional
        decision-making</li>
        <li>The model has consistently generated <strong>alpha over the Nifty 500 benchmark</strong>
        since inception, with a disciplined focus on both upside capture and
        downside protection</li>
      </ul>
    </div>
  </div>

  <!-- REBALANCE -->
  <div class="sec">
    <div class="sec-t">Rebalance Schedule</div>
    <div class="reb">
      <div class="ri"><div class="k">Frequency</div><div class="v">Monthly</div></div>
      <div class="ri"><div class="k">Rebalance Day</div><div class="v">1st Trading Day</div></div>
      <div class="ri"><div class="k">Last Rebalance</div><div class="v">August 2026</div></div>
      <div class="ri"><div class="k">Next Rebalance</div><div class="v">September 2026</div></div>
      <div class="ri"><div class="k">Managed By</div><div class="v" style="font-size:12px">SMC Research</div></div>
    </div>
  </div>

</div>

<!-- ═══════════ PAGE 2 ═══════════ -->
<div class="card brk">

  <!-- KEY METRICS -->
  <div class="sec">
    <div class="sec-t">Performance &amp; Risk Metrics</div>
    <div class="mg">
      <div>
        <div class="mr"><span class="k">CAGR (Portfolio)</span><span class="v g">{M['CAGR']:.2f}%</span></div>
        <div class="mr"><span class="k">CAGR (Nifty 500 &mdash; Benchmark)</span><span class="v n">{M['Bench_CAGR']:.2f}%</span></div>
        <div class="mr"><span class="k">CAGR (Nifty 50 &mdash; Reference)</span><span class="v n">{M['Bench_N50_CAGR']:.2f}%</span></div>
        <div class="mr"><span class="k">Total Return</span><span class="v g">{M['Total_Return']:.2f}%</span></div>
        <div class="mr"><span class="k">Alpha vs Nifty 500</span><span class="v g">+{M['Alpha']:.2f}%</span></div>
        <div class="mr"><span class="k">Annualised Volatility</span><span class="v n">{M['Volatility']:.2f}%</span></div>
        <div class="mr"><span class="k">Sharpe Ratio</span><span class="v g">{M['Sharpe']:.2f}</span></div>
        <div class="mr"><span class="k">Sortino Ratio</span><span class="v g">{M['Sortino']:.2f}</span></div>
        <div class="mr"><span class="k">Calmar Ratio</span><span class="v g">{M['Calmar']:.2f}</span></div>
      </div>
      <div>
        <div class="mr"><span class="k">Max Drawdown</span><span class="v r">{M['Max_DD']:.2f}%</span></div>
        <div class="mr"><span class="k">Win Rate (Monthly)</span><span class="v g">{M['Win_Rate']:.1f}%</span></div>
        <div class="mr"><span class="k">Avg Monthly Gain</span><span class="v g">+{M['Avg_Gain']:.2f}%</span></div>
        <div class="mr"><span class="k">Avg Monthly Loss</span><span class="v r">{M['Avg_Loss']:.2f}%</span></div>
        <div class="mr"><span class="k">Best Month</span><span class="v g">+{M['Best_Month']:.2f}%</span></div>
        <div class="mr"><span class="k">Worst Month</span><span class="v r">{M['Worst_Month']:.2f}%</span></div>
        <div class="mr"><span class="k">VaR (95%, Monthly)</span><span class="v r">{M['VaR_95']:.2f}%</span></div>
        <div class="mr"><span class="k">Live Since</span><span class="v n">Jan 2020</span></div>
      </div>
    </div>
  </div>

  <!-- SECTOR ALLOCATION -->
  <div class="sec">
    <div class="sec-t">Sector Allocation</div>
    {sector_rows}
  </div>

</div>

<!-- ═══════════ PAGE 3 ═══════════ -->
<div class="card brk">

  <!-- HOLDINGS -->
  <div class="sec">
    <div class="sec-t">Current Holdings &mdash; {len(portfolio)} Stocks &middot; August 2026</div>
    <div style="overflow-x:auto">
    <table>
      <thead><tr><th>#</th><th>Stock</th><th>Sector</th><th>Weight</th><th>LTP (₹)</th><th>Day Chg</th></tr></thead>
      <tbody>
{holdings_rows}
      </tbody>
    </table>
    </div>
  </div>

</div>

<!-- ═══════════ PAGE 4 ═══════════ -->
<div class="card brk">

  <!-- HOW IT WORKS -->
  <div class="sec">
    <div class="sec-t">How It Works</div>
    <div class="ig" style="grid-template-columns:repeat(4,1fr)">
      <div class="ic" style="text-align:center">
        <div style="font-size:22px;margin-bottom:6px">📊</div>
        <div class="k">Step 1</div>
        <div style="font-size:11.5px;color:var(--sub);margin-top:4px">SMC Research runs the proprietary quant model every month</div>
      </div>
      <div class="ic" style="text-align:center">
        <div style="font-size:22px;margin-bottom:6px">📋</div>
        <div class="k">Step 2</div>
        <div style="font-size:11.5px;color:var(--sub);margin-top:4px">Updated portfolio with buy/sell actions published on the dashboard</div>
      </div>
      <div class="ic" style="text-align:center">
        <div style="font-size:22px;margin-bottom:6px">💼</div>
        <div class="k">Step 3</div>
        <div style="font-size:11.5px;color:var(--sub);margin-top:4px">Execute the rebalance trades at the start of each month</div>
      </div>
      <div class="ic" style="text-align:center">
        <div style="font-size:22px;margin-bottom:6px">📈</div>
        <div class="k">Step 4</div>
        <div style="font-size:11.5px;color:var(--sub);margin-top:4px">Hold for 3–5 years for best risk-adjusted returns</div>
      </div>
    </div>
  </div>

  <!-- RISK FACTORS -->
  <div class="sec">
    <div class="sec-t">Key Risk Factors</div>
    <div class="rg">
      <div class="rc">
        <div class="rk">Market Risk</div>
        <p>Equity prices can decline sharply due to macroeconomic, geopolitical or company-specific factors. The portfolio has seen a maximum drawdown of {M['Max_DD']:.2f}% over the backtest period.</p>
      </div>
      <div class="rc">
        <div class="rk">Concentration Risk</div>
        <p>The portfolio holds {len(portfolio)} stocks, but is top-heavy — the largest positions are capped at 10% each and the top 10 holdings account for roughly 76% of the portfolio. Sector concentration may arise during certain market phases.</p>
      </div>
      <div class="rc">
        <div class="rk">Model Risk</div>
        <p>Past performance is not a guarantee of future results. Quantitative models may underperform during regime changes or unprecedented market events.</p>
      </div>
      <div class="rc">
        <div class="rk">Liquidity Risk</div>
        <p>All constituents are NSE-listed. As the universe spans mid and small cap companies alongside large caps, some holdings may trade with lower volumes, and liquidity can be temporarily limited during extreme market stress.</p>
      </div>
    </div>
  </div>

  <!-- DEFINITIONS -->
  <div class="sec">
    <div class="sec-t">Definitions and Disclosures</div>
    <div style="font-size:11px;line-height:1.75;margin-bottom:16px">
      <p style="margin-bottom:10px"><strong style="color:var(--pri)">CAGR</strong> — Compound Annual Growth Rate is a measure of the growth of a
      portfolio. Returns generated each year differ; CAGR expresses them as the single annual
      rate that would produce the same terminal value over the period. For example, a portfolio
      returning 5%, 15% and &minus;7% over three years has a CAGR of 3.94%. In this factsheet CAGR
      is computed on backtested model data from January 2020 onwards.</p>
      <p style="margin-bottom:10px"><strong style="color:var(--pri)">Volatility Label</strong> — Daily changes in stock prices cause fluctuation in the
      value of your investment. Each portfolio is categorised into one of three buckets &mdash;
      High, Medium or Low Volatility &mdash; by comparing the portfolio's volatility against
      that of the Nifty 100 Index. This portfolio's annualised volatility is {M['Volatility']:.2f}%,
      placing it in the <strong>High Volatility</strong> bucket. High Volatility means changes
      in your investment value can be sudden and significant.</p>
      <p style="margin-bottom:10px"><strong style="color:var(--pri)">Investment Horizon</strong> — The manager's recommended holding duration.
      Short Term: &lt;1 year. Medium Term: 1&ndash;3 years. Long Term: &gt;3 years. This portfolio is
      recommended as <strong>Long Term</strong>.</p>
      <p style="margin-bottom:10px"><strong style="color:var(--pri)">Asset Class</strong> — Constituents are selected from a universe defined by the
      manager, and that universe is labelled the Asset Class. All NSE-listed stocks are ranked in
      decreasing order of market capitalisation: ranks 1&ndash;100 are Large Cap, 101&ndash;250 are Mid Cap,
      and above 250 are Small Cap. This portfolio is <strong>Equity Multi Cap</strong>, meaning
      constituents may be drawn from more than two of the Large, Mid and Small Cap categories.</p>
      <p style="margin-bottom:10px"><strong style="color:var(--pri)">Rebalance</strong> — The process of periodically reviewing and updating the
      constituents of a portfolio, so that the holdings continue to reflect the underlying strategy.
      This portfolio is rebalanced <strong>monthly</strong>, on the first trading day of each month.</p>
      <p style="margin-bottom:10px"><strong style="color:var(--pri)">Holdings Distribution</strong> — Constituents are grouped into segments, and the
      weight of a segment is the sum of the weights of all constituents in it. For example, if four
      constituents of 10% each are Large Cap, the Large Cap segment weight is 40%.</p>
      <p><strong style="color:var(--pri)">Benchmark</strong> — Portfolio performance in this factsheet is compared against the
      <strong>Nifty 500</strong> (CAGR {M['Bench_CAGR']:.2f}% over the same period), which is the
      index CASE Platforms designates for the Equity Multi Cap asset class and is therefore the
      appropriate comparison for this portfolio. The <strong>Nifty 50</strong> (CAGR
      {M['Bench_N50_CAGR']:.2f}%) is shown alongside as a secondary broad-market reference only.
      Alpha is stated against the Nifty 500.</p>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 28px;font-size:11px;line-height:1.7">
      <div><strong>CAGR:</strong> Compound Annual Growth Rate — annualised return over the full period.</div>
      <div><strong>Sharpe Ratio:</strong> Risk-adjusted return per unit of total volatility.</div>
      <div><strong>Sortino Ratio:</strong> Risk-adjusted return penalising only downside deviation.</div>
      <div><strong>Calmar Ratio:</strong> CAGR divided by maximum drawdown.</div>
      <div><strong>Max Drawdown:</strong> Largest peak-to-trough decline during the period.</div>
      <div><strong>Win Rate:</strong> Percentage of months with positive returns.</div>
      <div><strong>Alpha:</strong> Portfolio CAGR minus Nifty 500 benchmark CAGR.</div>
      <div><strong>VaR (95%):</strong> Worst expected monthly loss at 95% confidence.</div>
    </div>
  </div>

  <!-- DISCLAIMER -->
  <div class="sec">
    <div class="sec-t">General Investment Disclosure</div>
    <div class="disc">
      <strong>⚠ IMPORTANT:</strong> This factsheet is for <strong>informational purposes only</strong>
      and does not constitute investment advice, solicitation, or a recommendation to buy
      or sell any securities. Past performance is not indicative of future results.
      Investments in the securities market are subject to market risks. Read all related
      documents carefully before investing.
      <br><br>
      The performance data shown is based on a quantitative model simulation. Live
      performance may differ from model results due to transaction costs, taxes (STT, GST),
      impact cost, and execution timing. The portfolio is rebalanced monthly at month-open
      prices. <strong>All returns, CAGR and risk figures shown in this factsheet are derived
      from backtested model data covering January 2020 onwards, and do not represent the
      returns of an actual live-traded portfolio.</strong> Backtested results are hypothetical,
      are computed with the benefit of hindsight, and have inherent limitations. They have not
      been validated by an independent chartered accountant, nor verified by the Past Risk and
      Return Verification Agency (PaRRVA) or any other agency recognised by SEBI.
      <br><br>
      The volatility label (High/Medium/Low) is determined by comparing the portfolio's
      daily volatility against the Nifty 100 Index. High Volatility means that changes in
      your investment value can be sudden and significant.
    </div>
  </div>

  <!-- RISK DISCLOSURE -->
  <div class="sec">
    <div class="sec-t">Risk Disclosure</div>
    <div class="disc">
      Investing in securities involves various types of risk that may impact your investment.
      Key risks affecting all asset classes include changes in: market volatility; general
      market conditions; trading volumes, liquidity and settlement periods; interest rates;
      the rate of inflation; domestic and global political, economic and financial
      developments; and policies, legal or regulatory frameworks set by government and other
      appropriate authorities.
      <br><br>
      <strong>Risks relating to equity and equity-linked investments:</strong> equity shares and
      equity-related instruments are volatile and prone to price fluctuation on a daily basis.
      Prices may be affected by trading volume volatility, currency exchange rates, company
      specific news and rumours, and other factors. <strong>Mid cap and small cap stocks generally
      exhibit higher volatility than large cap stocks.</strong> As this is a Multi Cap portfolio
      that draws from the full NSE universe, a meaningful portion of the holdings may fall in
      the mid and small cap segments at any given time.
      <br><br>
      In light of the risks involved, you should transact in securities only after understanding
      the associated risks. Please consider and assess all risk factors and your own risk
      tolerance before making investment decisions.
    </div>
  </div>

  <!-- MANAGER DISCLOSURE -->
  <div class="sec">
    <div class="sec-t">Manager Disclosure</div>
    <div class="disc">
      <strong>SMC Global Securities Ltd.</strong> is registered with SEBI as a Research Analyst,
      with its registered office at 11/6B, Shanti Chamber, Pusa Road, New Delhi &ndash; 110005.
      Registration granted by SEBI and certification from NISM in no way guarantee performance
      of the intermediary or provide any assurance of returns to investors.
      <br><br>
      The content and data available in this material, including index values, return numbers
      and rationale, are for information and illustration purposes only. Charts and performance
      numbers do not include the impact of transaction fees and other related costs. Past
      performance does not guarantee future returns and the performance of the portfolio is
      subject to market risk. Data used for the calculation of historical returns and other
      information is sourced from exchange-approved third party vendors and has neither been
      audited nor independently validated.
      <br><br>
      Information presented in this material shall not be considered a recommendation or
      solicitation of an investment. Investors are responsible for their own investment
      decisions and for validating all information used to make those decisions.
      <br><br>
      This document is solely for the personal information of the recipient and must not
      be used as the basis of any investment decision. Nothing in this document should be
      construed as investment or financial advice. The report and information contained
      herein may not be altered, reproduced, or redistributed without prior written consent.
    </div>
  </div>

</div>

<!-- FOOTER -->
<div class="ft" style="margin-bottom:0">
  <strong>SMC Research — Moneywise. Be Wise.</strong><br>
  SQE SmallCase · All Indices Portfolio · Monthly Rebalanced<br>
  <a href="https://smcresearch.github.io/SQE-/">smcresearch.github.io/SQE-/</a>
  &nbsp;·&nbsp; Generated: {last_update_fmt}
</div>

</div>
<button class="pbtn no-print" onclick="window.print()">🖨️ Print / Save PDF</button>
</body>
</html>'''

OUT_DIR  = Path(r'd:/SQE-host')
HTML_OUT = OUT_DIR / 'factsheet.html'
PDF_OUT  = OUT_DIR / 'SQE_Factsheet.pdf'

HTML_OUT.write_text(html, encoding='utf-8')
print(f'factsheet.html generated -- {len(portfolio)} holdings, updated {last_update_fmt}')


def find_chrome():
    """Locate a Chromium-based browser to render the PDF with."""
    candidates = [
        r'C:/Program Files/Google/Chrome/Application/chrome.exe',
        r'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
        r'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
        r'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    ]
    return next((c for c in candidates if Path(c).exists()), None)


chrome = find_chrome()
if not chrome:
    print('WARNING: no Chrome/Edge found -- PDF not generated. '
          'Open factsheet.html and use Print > Save as PDF.')
else:
    # Render from a file:// URL so the relative smc_logo.webp reference resolves.
    with tempfile.TemporaryDirectory() as profile:
        cmd = [
            chrome, '--headless', '--disable-gpu', '--no-sandbox',
            f'--user-data-dir={profile}',
            '--no-pdf-header-footer',
            '--print-to-pdf-no-header',
            f'--print-to-pdf={PDF_OUT}',
            HTML_OUT.as_uri(),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if PDF_OUT.exists() and PDF_OUT.stat().st_size > 0:
        print(f'{PDF_OUT.name} generated -- {PDF_OUT.stat().st_size/1024:.0f} KB')
    else:
        print('WARNING: PDF render failed.')
        print((res.stderr or res.stdout or '').strip()[:500])
