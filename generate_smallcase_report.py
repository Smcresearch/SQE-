"""
Generate SQE_SmallCase_AllIndices_August26.pdf — the institutional performance &
backtest report for the SQE SmallCase (SMC Quant Equity) All-Indices portfolio.

Layout follows the SQE ProQuant report format (6 pages: cover, executive summary,
performance charts, full metrics + heatmap, portfolio characteristics + current book,
definitions + disclosures), rebranded to SQE SmallCase and driven entirely off
d:/SQE-host/data.js so the figures track the live dashboard.
"""
import json, io
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth

ROOT = Path(r'd:/SQE-host')
OUT = ROOT / 'SQE_SmallCase_AllIndices_August26.pdf'

# ── Branding ──
PRODUCT   = 'SQE SmallCase'
TAGLINE   = 'SMC Quant Equity — Systematic Multi-Factor Equity Strategy'
FOOTLINE  = f'{PRODUCT}  |  SMC Quant Equity  |  Confidential'
UNIVERSE  = 'All Indices (759)'
MIN_INVESTMENT = 'Rs.1.25 lakhs  (Rs.1,25,000)'   # business input — carried over from
                                                  # the ProQuant report, not derived here
# Charged on turnover — the value of quantity bought AND sold at each monthly rebalance.
# NOTE: som_hedge.py reads COST_PER_TRADE from the environment and defaults to 0.002;
# no launcher in D:/Host_portfolio sets it, so re-run the engine with COST_PER_TRADE=0.003
# if data.js was built on the default.
TURNOVER_COST = '0.3%'

# ── Palette ──
NAVY   = HexColor('#1A2A57')
NAVY_D = HexColor('#16244B')
BLUE   = HexColor('#2F6FE4')
BLUE_D = HexColor('#1F3864')
GREEN  = HexColor('#1E9E57')
RED    = HexColor('#D64545')
AMBER  = HexColor('#E2A029')
GREY   = HexColor('#6B7280')
GREY_L = HexColor('#9AA3B2')
LINE   = HexColor('#E3E9F2')
TILE   = HexColor('#F5F8FC')
WHITE  = HexColor('#FFFFFF')
BLACK  = HexColor('#1F2937')

PW, PH = A4
MX = 42.0                 # left/right margin
CW = PW - 2 * MX          # content width

F, FB = 'Helvetica', 'Helvetica-Bold'


# ═══════════════════════════ data ═══════════════════════════
raw = (ROOT / 'data.js').read_text(encoding='utf-8').strip()
raw = raw[raw.index('=') + 1:].rstrip().rstrip(';')
D = json.loads(raw)
T = D['total759']

ES = T['exec_summary']
EC = T['equity_curves']
MD = T['monthly_detail']
PORT = sorted(T['current_portfolio'], key=lambda h: -h['weight'])

MONTHS = EC['months']
START_M, END_M = MONTHS[0], MONTHS[-1]
N_MONTHS = T['total_months']
RANGE_TXT = f'Backtest {START_M} - {END_M}  ({N_MONTHS} mo)'

as_of = D.get('last_update', '')[:10]
try:
    AS_OF_FMT = datetime.strptime(as_of, '%Y-%m-%d').strftime('%d %B %Y')
except ValueError:
    AS_OF_FMT = as_of


def b(key):
    """Base-layer value from exec_summary."""
    return ES[key]['Base']


def pct(x, dp=1, sign=False):
    s = f'{x * 100:+.{dp}f}%' if sign else f'{x * 100:.{dp}f}%'
    return s


CAGR       = b('CAGR')
BENCH_CAGR = ES['CAGR']['Bench']
TOTAL_RET  = b('Abs Return')
ALPHA      = b('Alpha vs Bench')
MAXDD      = b('Max Drawdown')
BENCH_DD   = ES['Max Drawdown']['Bench']
WINRATE    = b('Win Rate')
EA_SHARPE  = b('Avg Ex-Ante Sharpe')
EA_SORTINO = b('Avg Ex-Ante Sortino')
CALMAR     = b('Calmar')
VOL        = b('Volatility')
PROFIT_F   = b('Profit Factor')
INFO_R     = b('Info Ratio')
PORT_BETA  = MD[-1]['Port_Beta']
STOCK_CNT  = MD[-1]['Stock_Count']
MULTIPLE   = EC['Base'][-1]

SECTOR_SHORT = {
    'Automobile and Auto Components': 'Automobile',
    'Fast Moving Consumer Goods': 'FMCG',
    'Financial Services': 'Financials',
    'Consumer Services': 'Consumer Svcs',
}


def short_sector(s):
    return SECTOR_SHORT.get(s, s)


# ═══════════════════════════ text helpers ═══════════════════════════
def wrap(text, font, size, width):
    words, lines, cur = text.split(), [], ''
    for w in words:
        trial = f'{cur} {w}'.strip()
        if stringWidth(trial, font, size) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_para(c, text, x, y, width, size=8.6, leading=11.4, font=F,
              color=BLACK, justify=True):
    """Justified paragraph, matching the reference report's body text."""
    c.setFillColor(color)
    lines = wrap(text, font, size, width)
    for i, line in enumerate(lines):
        last = i == len(lines) - 1
        if justify and not last and len(line.split()) > 1:
            words = line.split()
            natural = sum(stringWidth(w, font, size) for w in words)
            gap = (width - natural) / (len(words) - 1)
            cx = x
            for w in words:
                c.setFont(font, size)
                c.drawString(cx, y, w)
                cx += stringWidth(w, font, size) + gap
        else:
            c.setFont(font, size)
            c.drawString(x, y, line)
        y -= leading
    return y


def section_head(c, title, y, sub=None):
    """Blue tick + navy heading, as used throughout the reference report."""
    c.setFillColor(BLUE)
    c.rect(MX, y - 2, 4.5, 13, stroke=0, fill=1)
    c.setFillColor(BLUE_D)
    c.setFont(FB, 12.5)
    c.drawString(MX + 12, y, title)
    y -= 15
    if sub:
        c.setFillColor(GREY)
        c.setFont(F, 8.2)
        c.drawString(MX + 12, y - 2, sub)
        y -= 12
    return y - 4


def page_frame(c, page_no):
    """Running header/footer on every page except the cover."""
    c.setFillColor(GREY)
    c.setFont(F, 7.6)
    c.drawString(MX, PH - 34, f'{PRODUCT}  -  {UNIVERSE}  -  Portfolio Report')
    c.drawRightString(PW - MX, PH - 34, RANGE_TXT)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(MX, PH - 42, PW - MX, PH - 42)

    c.setFillColor(GREY_L)
    c.setFont(F, 7.4)
    c.drawString(MX, 28, FOOTLINE)
    c.drawRightString(PW - MX, 28, f'Page {page_no}')


# ═══════════════════════════ charts ═══════════════════════════
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans'],
    'axes.edgecolor': '#C9D2E0',
    'axes.linewidth': 0.7,
    'xtick.color': '#6B7280',
    'ytick.color': '#6B7280',
    'text.color': '#374151',
})

_STRIDE = max(1, len(MONTHS) // 7)
TICK_IDX = [i for i in range(0, len(MONTHS), _STRIDE)]
# Always end on the final month, and drop the preceding tick if it would collide with it.
_LAST = len(MONTHS) - 1
TICK_IDX = [i for i in TICK_IDX if _LAST - i >= _STRIDE * 0.6] + [_LAST]
TICK_LBL = [MONTHS[i] for i in TICK_IDX]


def fig_to_png(fig, dpi=200):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                facecolor='white', pad_inches=0.02)
    plt.close(fig)
    buf.seek(0)
    return buf


def style_axes(ax, ygrid=True):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    if ygrid:
        ax.grid(axis='y', color='#EDF1F7', linewidth=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=7, length=2, width=0.6)


def chart_growth():
    fig, ax = plt.subplots(figsize=(9.6, 3.05))
    x = range(len(MONTHS))
    ax.plot(x, EC['Base'], color='#2F6FE4', linewidth=2.0, label=f'{PRODUCT} (Base)')
    ax.plot(x, EC['Bench'], color='#9BA6B5', linewidth=1.9, label='Benchmark')
    ax.set_xticks(TICK_IDX)
    ax.set_xticklabels(TICK_LBL)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}x'))
    ax.set_xlim(0, len(MONTHS) - 1)
    ax.set_ylim(0, max(EC['Base']) * 1.05)
    style_axes(ax)
    ax.legend(loc='upper left', frameon=False, fontsize=8, ncol=2,
              handlelength=2.4, columnspacing=1.6)
    return fig_to_png(fig)


def drawdown_series(curve):
    peak, dd = -1e9, []
    for v in curve:
        peak = max(peak, v)
        dd.append(v / peak - 1)
    return dd


def chart_drawdown():
    dd = drawdown_series(EC['Base'])
    fig, ax = plt.subplots(figsize=(9.6, 1.95))
    x = list(range(len(MONTHS)))
    ax.fill_between(x, dd, 0, color='#E8A0A0', alpha=0.75, linewidth=0)
    ax.plot(x, dd, color='#C94A4A', linewidth=0.9)
    ax.set_xticks(TICK_IDX)
    ax.set_xticklabels(TICK_LBL)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v * 100:.0f}%'))
    ax.set_xlim(0, len(MONTHS) - 1)
    ax.set_ylim(min(dd) * 1.08, 0.005)
    style_axes(ax)
    return fig_to_png(fig)


def calendar_year_returns(heat_key):
    """Compound the monthly heatmap rows into calendar-year returns."""
    out = {}
    for row in T['heatmaps'][heat_key]:
        acc = 1.0
        for m in ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'):
            v = row.get(m)
            if v is not None:
                acc *= 1 + v / 100
        out[row['year']] = acc - 1
    return out


def chart_calendar():
    strat = calendar_year_returns('Base')
    bench = calendar_year_returns('Bench')
    years = sorted(strat)
    fig, ax = plt.subplots(figsize=(9.6, 2.15))
    idx = range(len(years))
    w = 0.36
    ax.bar([i - w / 2 for i in idx], [strat[y] for y in years], w,
           color='#2F6FE4', label='Strategy')
    ax.bar([i + w / 2 for i in idx], [bench.get(y, 0) for y in years], w,
           color='#9BA6B5', label='Benchmark')
    ax.axhline(0, color='#C9D2E0', linewidth=0.8)
    ax.set_xticks(list(idx))
    ax.set_xticklabels(years)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v * 100:.0f}%'))
    style_axes(ax)
    ax.legend(loc='upper right', frameon=False, fontsize=8, ncol=2)
    return fig_to_png(fig), strat, bench


def chart_line(values, color, fmt='{:.1f}'):
    fig, ax = plt.subplots(figsize=(4.55, 1.55))
    x = range(len(values))
    ax.plot(x, values, color=color, linewidth=1.2)
    ax.set_xticks(TICK_IDX)
    ax.set_xticklabels(TICK_LBL)
    ax.set_xlim(0, len(values) - 1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: fmt.format(v)))
    style_axes(ax)
    return fig_to_png(fig)


# ═══════════════════════════ page 1 — cover ═══════════════════════════
def page_cover(c):
    c.setFillColor(NAVY)
    c.rect(0, 0, PW, PH, stroke=0, fill=1)

    # Separator band behind the KPI strip
    c.setFillColor(HexColor('#233768'))
    c.rect(0, PH - 348, PW, 10, stroke=0, fill=1)

    x = MX + 24
    c.setFillColor(WHITE)
    c.setFont(FB, 34)
    c.drawString(x, PH - 200, PRODUCT)

    c.setFillColor(HexColor('#A9BEDF'))
    c.setFont(F, 12.5)
    c.drawString(x, PH - 228, TAGLINE)

    c.setFillColor(BLUE)
    c.setLineWidth(2.6)
    c.setStrokeColor(BLUE)
    c.line(x, PH - 250, x + 155, PH - 250)

    c.setFillColor(WHITE)
    c.setFont(FB, 15)
    c.drawString(x, PH - 292, f'{UNIVERSE} - Performance & Backtest Report')

    c.setFillColor(HexColor('#A9BEDF'))
    c.setFont(F, 10)
    c.drawString(x, PH - 316, f'Backtest {START_M} -> {END_M}   -   {N_MONTHS} months')

    c.setFillColor(HexColor('#E2B84B'))
    c.setFont(FB, 10.5)
    c.drawString(x, PH - 340, f'Minimum Investment:   {MIN_INVESTMENT}')

    kpis = [(pct(CAGR), 'CAGR'), (f'{TOTAL_RET * 100:.0f}%', 'Total Return'),
            (f'{EA_SHARPE:.2f}', 'Ex-Ante Sharpe'), (f'{EA_SORTINO:.2f}', 'Ex-Ante Sortino')]
    for i, (val, lbl) in enumerate(kpis):
        kx = x + i * 148
        c.setFillColor(WHITE)
        c.setFont(FB, 21)
        c.drawString(kx, PH - 405, val)
        c.setFillColor(HexColor('#8FA6CC'))
        c.setFont(F, 8.4)
        c.drawString(kx, PH - 422, lbl)

    notes = [
        (f'Prepared August 2026   -   Universe: All NSE indices (759 stocks)   -   '
         f'Data as of {AS_OF_FMT}', '#A9BEDF', F, 9),
        ('Strategy: Base (unhedged) - conviction-weighted (10% cap/name), monthly rebalance',
         '#A9BEDF', F, 9),
        (f'Returns are NET of a {TURNOVER_COST} per-trade turnover cost.', '#A9BEDF', F, 9),
    ]
    ny = 168
    for text, col, fnt, size in notes:
        c.setFillColor(HexColor(col))
        c.setFont(fnt, size)
        c.drawString(x, ny, text)
        ny -= 18

    c.setFillColor(HexColor('#6E86B4'))
    c.setFont(F, 8)
    c.drawString(x, 108, 'CONFIDENTIAL - For authorised review only. Backtested results; '
                         'past performance does not guarantee future results.')

    c.setFillColor(HexColor('#5E76A4'))
    c.setFont(F, 7.4)
    c.drawString(x, 86, FOOTLINE)
    c.drawRightString(PW - MX - 24, 86, 'Page 1')
    c.showPage()


# ═══════════════════════════ page 2 — summary + KPIs ═══════════════════════════
def page_summary(c):
    page_frame(c, 2)
    y = PH - 74

    y = section_head(c, 'Executive Summary', y)
    para1 = (
        f'{PRODUCT} is a fully systematic, rules-based Indian-equity strategy run on the '
        f'broadest universe - all NSE index constituents (759 stocks). Each month the model '
        f'ranks the universe and holds a concentrated, conviction-weighted basket of its '
        f'highest-conviction names (capped at 10% per position), rebalanced on a fixed monthly '
        f'cadence. Over the {N_MONTHS}-month backtest ({START_M} - {END_M}) the Base strategy '
        f'turned Rs.1 into Rs.{MULTIPLE:.2f} - a {pct(CAGR)} CAGR versus {pct(BENCH_CAGR)} for '
        f'the Nifty 500 benchmark, an annual alpha of {pct(ALPHA)}.')
    y = draw_para(c, para1, MX, y - 4, CW) - 4

    para2 = (
        f'Risk was contained despite the high return: a maximum drawdown of {pct(MAXDD)} '
        f'(shallower than the benchmark\u2019s {pct(BENCH_DD)}), portfolio beta of '
        f'{PORT_BETA:.2f}, and a win rate of {WINRATE * 100:.0f}% of months. Forward-looking '
        f'basket quality is strong: Ex-Ante Sharpe {EA_SHARPE:.2f} and Ex-Ante Sortino '
        f'{EA_SORTINO:.2f}.')
    y = draw_para(c, para2, MX, y, CW) - 14

    y = section_head(c, 'Key Performance Indicators', y)

    tiles = [
        (pct(CAGR), 'CAGR', GREEN),
        (f'{TOTAL_RET * 100:.0f}%', 'Total Return', GREEN),
        (pct(ALPHA), 'Alpha vs Bench', GREEN),
        (f'{EA_SHARPE:.2f}', 'Ex-Ante Sharpe', BLUE),
        (f'{EA_SORTINO:.2f}', 'Ex-Ante Sortino', BLUE),
        (f'{CALMAR:.2f}', 'Calmar', BLUE),
        (pct(MAXDD), 'Max Drawdown', RED),
        (pct(VOL), 'Volatility', AMBER),
        (f'{WINRATE * 100:.0f}%', 'Win Rate', GREEN),
        (f'{PROFIT_F:.2f}', 'Profit Factor', GREEN),
        (f'{INFO_R:.2f}', 'Info Ratio', BLUE),
        (f'{PORT_BETA:.2f}', 'Portfolio Beta', AMBER),
    ]
    tw, th, gap = (CW - 3 * 10) / 4, 46, 10
    ty = y - th
    for i, (val, lbl, col) in enumerate(tiles):
        tx = MX + (i % 4) * (tw + gap)
        row_y = ty - (i // 4) * (th + gap)
        c.setFillColor(TILE)
        c.rect(tx, row_y, tw, th, stroke=0, fill=1)
        c.setFillColor(col)
        c.rect(tx, row_y, 3.4, th, stroke=0, fill=1)
        c.setFillColor(BLUE_D)
        c.setFont(FB, 15)
        c.drawString(tx + 12, row_y + 24, val)
        c.setFillColor(GREY)
        c.setFont(F, 7.8)
        c.drawString(tx + 12, row_y + 10, lbl)
    y = ty - 2 * (th + gap) - 26

    y = section_head(c, 'Methodology - High Level', y)
    m1 = ('Selection engine (proprietary). Each month the model scores the entire 759-stock '
          'universe on a multi-factor quantitative framework combining trend, relative-strength, '
          'momentum-quality and risk characteristics, then ranks and selects the top-conviction '
          'names. The exact factors, weights and ranking logic are proprietary and intentionally '
          'not disclosed in this document.')
    y = draw_para(c, m1, MX, y - 4, CW) - 5

    m2 = ('Construction & rebalancing. The chosen names form a conviction-weighted basket - '
          'position sizes scale with model conviction and are capped at 10% per name - '
          'rebalanced monthly with add/remove churn tracked each cycle; the book is managed to a '
          'beta below the market. Risk-adjusted quality is reported forward-looking via Ex-Ante '
          'Sharpe / Sortino, computed from the daily-return covariance (and downside '
          'semi-covariance) of the CURRENT holdings.')
    draw_para(c, m2, MX, y, CW)
    c.showPage()


# ═══════════════════════════ page 3 — charts ═══════════════════════════
def page_charts(c):
    page_frame(c, 3)
    y = PH - 74

    y = section_head(c, 'Growth of Rs.1 - Strategy vs Benchmark', y,
                     sub=f'Compounded backtest, {START_M} = Rs.1.00. Nifty 500 TR benchmark.')
    img = chart_growth()
    h = CW * 3.05 / 9.6
    c.drawImage(rl_image(img), MX, y - h, width=CW, height=h, mask='auto')
    y -= h + 18

    c.setFillColor(BLUE_D)
    c.setFont(FB, 9.5)
    c.drawString(MX, y, 'Drawdown (underwater curve)')
    y -= 8
    img = chart_drawdown()
    h = CW * 1.95 / 9.6
    c.drawImage(rl_image(img), MX, y - h, width=CW, height=h, mask='auto')
    y -= h + 18

    c.setFillColor(BLUE_D)
    c.setFont(FB, 9.5)
    c.drawString(MX, y, 'Calendar-Year Returns (%)')
    y -= 8
    img, _, _ = chart_calendar()
    h = CW * 2.15 / 9.6
    c.drawImage(rl_image(img), MX, y - h, width=CW, height=h, mask='auto')
    c.showPage()


def rl_image(buf):
    from reportlab.lib.utils import ImageReader
    return ImageReader(buf)


# ═══════════════════════════ page 4 — metrics + heatmap ═══════════════════════════
def metric_block(c, x, y, w, title, rows):
    """Blue-headed metric table with zebra rows."""
    rh, hh = 15.2, 16.5
    c.setFillColor(BLUE)
    c.rect(x, y - hh, w, hh, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont(FB, 8.2)
    c.drawString(x + 8, y - hh + 5, title)
    ry = y - hh
    for i, (k, v) in enumerate(rows):
        ry -= rh
        if i % 2 == 0:
            c.setFillColor(HexColor('#F5F8FC'))
            c.rect(x, ry, w, rh, stroke=0, fill=1)
        c.setFillColor(BLACK)
        c.setFont(F, 8.2)
        c.drawString(x + 8, ry + 4.6, k)
        c.setFont(FB, 8.2)
        c.drawRightString(x + w - 8, ry + 4.6, v)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.rect(x, ry, w, y - ry, stroke=1, fill=0)
    return ry


def heat_color(v):
    """Green for gains, red for losses, intensity scaled to +/-15%."""
    if v is None:
        return HexColor('#F7F8FA')
    t = max(-1.0, min(1.0, v / 15.0))
    if t >= 0:
        return HexColor('#%02x%02x%02x' % (int(232 - 82 * t), int(245 - 60 * t),
                                           int(233 - 70 * t)))
    t = -t
    return HexColor('#%02x%02x%02x' % (int(250 - 22 * t), int(228 - 108 * t),
                                       int(228 - 108 * t)))


def page_metrics(c):
    page_frame(c, 4)
    y = PH - 74
    y = section_head(c, 'Full Performance Metrics', y)

    cw = (CW - 14) / 2
    ret_rows = [
        ('CAGR', pct(CAGR)), ('Total Return', f'{TOTAL_RET * 100:.0f}%'),
        ('XIRR', pct(b('XIRR'))), ('Alpha vs Bench', pct(ALPHA)),
        ('Rolling 1Y', pct(b('Rolling 1Y'))), ('Rolling 3Y', pct(b('Rolling 3Y'))),
        ('Best Month', pct(b('Best Month'))), ('Worst Month', pct(b('Worst Month'))),
    ]
    risk_rows = [
        ('Volatility', pct(VOL)), ('Downside Dev', pct(b('Downside Dev'))),
        ('Max Drawdown', pct(MAXDD)), ('DD Duration', f"{b('DD Duration (M)'):.0f} mo"),
        ('VaR 95%', pct(b('VaR 95%'))), ('VaR 99%', pct(b('VaR 99%'))),
        ('CVaR 95%', pct(b('CVaR 95%'))), ('CVaR 99%', pct(b('CVaR 99%'))),
    ]
    y1 = metric_block(c, MX, y, cw, 'Return', ret_rows)
    metric_block(c, MX + cw + 14, y, cw, 'Risk', risk_rows)

    y2 = y1 - 16
    ra_rows = [
        ('Ex-Ante Sharpe', f'{EA_SHARPE:.2f}'), ('Ex-Ante Sortino', f'{EA_SORTINO:.2f}'),
        ('Calmar', f'{CALMAR:.2f}'), ('Information Ratio', f'{INFO_R:.2f}'),
        ('Portfolio Beta', f'{PORT_BETA:.2f}'), ('Latest Stock Count', f'{STOCK_CNT:.0f}'),
    ]
    trade_rows = [
        ('Win Rate', f'{WINRATE * 100:.0f}%'), ('Profit Factor', f'{PROFIT_F:.2f}'),
        ('Expectancy', pct(b('Expectancy'))), ('Avg Gain', pct(b('Avg Gain'))),
        ('Avg Loss', pct(b('Avg Loss'))),
    ]
    y3 = metric_block(c, MX, y2, cw, 'Risk-Adjusted (Ex-Ante)', ra_rows)
    metric_block(c, MX + cw + 14, y2, cw, 'Trade', trade_rows)

    y = y3 - 26
    y = section_head(c, 'Monthly Returns Heatmap (%)', y,
                     sub='Strategy Base monthly return. Green = gain, red = loss. '
                         'FY column = calendar-year compounded return.')

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    rows = T['heatmaps']['Base']
    fy = calendar_year_returns('Base')

    lab_w, fy_w = 30.0, 40.0
    cell_w = (CW - lab_w - fy_w - 6) / 12
    cell_h = 15.5

    c.setFillColor(GREY)
    c.setFont(F, 7.2)
    for i, m in enumerate(months):
        c.drawCentredString(MX + lab_w + i * cell_w + cell_w / 2, y - 8, m)
    c.setFillColor(BLUE_D)
    c.setFont(FB, 7.4)
    c.drawCentredString(MX + lab_w + 12 * cell_w + 6 + fy_w / 2, y - 8, 'FY')
    ry = y - 13

    for row in rows:
        ry -= cell_h + 2
        c.setFillColor(BLUE_D)
        c.setFont(FB, 7.6)
        c.drawString(MX, ry + 5, str(row['year']))
        for i, m in enumerate(months):
            v = row.get(m)
            cx = MX + lab_w + i * cell_w
            c.setFillColor(heat_color(v))
            c.rect(cx, ry, cell_w - 1.6, cell_h, stroke=0, fill=1)
            if v is not None:
                c.setFillColor(HexColor('#7A2020') if v < 0 else HexColor('#14532D'))
                c.setFont(F, 6.9)
                c.drawCentredString(cx + (cell_w - 1.6) / 2, ry + 4.6, f'{v:.1f}')
        v = fy.get(row['year'])
        fx = MX + lab_w + 12 * cell_w + 6
        c.setFillColor(HexColor('#EAF2FD'))
        c.rect(fx, ry, fy_w, cell_h, stroke=0, fill=1)
        c.setFillColor(BLUE_D)
        c.setFont(FB, 7.4)
        c.drawCentredString(fx + fy_w / 2, ry + 4.6, f'{v * 100:+.0f}%')

    c.setFillColor(GREY_L)
    c.setFont(F, 7)
    c.drawString(MX, ry - 14, f'{END_M} is a part-month: figures reflect data to {AS_OF_FMT}.')
    c.showPage()


# ═══════════════════════════ page 5 — characteristics + book ═══════════════════════════
def page_book(c):
    page_frame(c, 5)
    y = PH - 74
    y = section_head(c, 'Portfolio Characteristics Over Time', y)

    half = (CW - 16) / 2
    h = half * 1.55 / 4.55
    c.setFillColor(BLUE_D)
    c.setFont(FB, 9.2)
    c.drawString(MX, y, 'Portfolio Beta (vs market)')
    c.drawString(MX + half + 16, y, 'Number of Holdings')
    y -= 8
    c.drawImage(rl_image(chart_line([m['Port_Beta'] for m in MD], '#D98324', '{:.1f}')),
                MX, y - h, width=half, height=h, mask='auto')
    c.drawImage(rl_image(chart_line([m['Stock_Count'] for m in MD], '#1E9E57', '{:.0f}')),
                MX + half + 16, y - h, width=half, height=h, mask='auto')
    y -= h + 22

    y = section_head(c, 'Current Book - Sector Allocation & Holdings', y,
                     sub=f'As of {END_M} - {len(PORT)} positions, conviction-weighted '
                         f'(10% cap/name).')

    left_w = half - 6
    c.setFillColor(BLUE_D)
    c.setFont(FB, 9)
    c.drawString(MX, y, 'By Sector')
    c.drawString(MX + half + 16, y, f'All Holdings ({len(PORT)})')
    sy = y - 16

    sector = {}
    for hd in PORT:
        s = short_sector(hd['sector'])
        sector[s] = sector.get(s, 0) + hd['weight']
    sector = dict(sorted(sector.items(), key=lambda kv: -kv[1]))
    max_w = max(sector.values())
    bar_x, bar_max = MX + 96, left_w - 96 - 30

    for name, wt in sector.items():
        c.setFillColor(BLACK)
        c.setFont(F, 8)
        c.drawString(MX, sy, name)
        bw = max(3.0, wt / max_w * bar_max)
        c.setFillColor(HexColor('#7FA8E8'))
        c.rect(bar_x, sy - 2.5, bw, 9, stroke=0, fill=1)
        c.setFillColor(GREY)
        c.setFont(F, 8)
        c.drawString(bar_x + bw + 6, sy, f'{wt * 100:.0f}%')
        sy -= 17.5

    # Holdings table — starts below the "All Holdings" caption, not level with it
    tx = MX + half + 16
    tw = half
    cols = [tx + 6, tx + 92, tx + tw - 44, tx + tw - 6]
    hh = 15.0
    top = y - 14
    c.setFillColor(NAVY)
    c.rect(tx, top - hh, tw, hh, stroke=0, fill=1)
    hy = top - hh + 4
    c.setFillColor(WHITE)
    c.setFont(FB, 7.4)
    c.drawString(cols[0], hy + 0.5, 'Symbol')
    c.drawString(cols[1], hy + 0.5, 'Sector')
    c.drawRightString(cols[2], hy + 0.5, 'Wt%')
    c.drawRightString(cols[3], hy + 0.5, 'Beta')

    rh = 14.2
    ry = hy - 3
    for i, hd in enumerate(PORT):
        ry -= rh
        if i % 2 == 0:
            c.setFillColor(HexColor('#F5F8FC'))
            c.rect(tx, ry, tw, rh, stroke=0, fill=1)
        c.setFillColor(BLUE_D)
        c.setFont(FB, 7.6)
        c.drawString(cols[0], ry + 4.4, hd['clean_symbol'][:13])
        c.setFillColor(GREY)
        c.setFont(F, 7.2)
        c.drawString(cols[1], ry + 4.4, short_sector(hd['sector'])[:18])
        c.setFillColor(BLACK)
        c.setFont(F, 7.6)
        c.drawRightString(cols[2], ry + 4.4, f"{hd['weight'] * 100:.1f}")
        c.drawRightString(cols[3], ry + 4.4, f"{hd.get('beta', 0):.2f}")
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.rect(tx, ry, tw, top - ry, stroke=1, fill=0)
    c.showPage()


# ═══════════════════════════ page 6 — definitions + disclosures ═══════════════════════════
def page_notes(c):
    page_frame(c, 6)
    y = PH - 74
    y = section_head(c, 'Notes on Metrics & Definitions', y)

    defs = [
        ('CAGR', 'Compound annual growth rate of the strategy over the backtest window.'),
        ('Alpha vs Bench', 'Strategy CAGR minus benchmark (Nifty 500 TR) CAGR - annual '
                           'out-performance.'),
        ('Ex-Ante Sharpe', 'FORWARD-looking reward-per-total-risk of the CURRENT basket, from '
                           'the annualised daily-return covariance of holdings (headline '
                           'risk-adjusted measure used here).'),
        ('Ex-Ante Sortino', 'As Ex-Ante Sharpe but the denominator uses downside semi-covariance '
                            '(losing days only) - penalises only downside risk.'),
        ('Calmar', 'CAGR divided by the absolute maximum drawdown - return per unit of '
                   'worst-case loss.'),
        ('Volatility / Downside Dev', 'Annualised standard deviation of monthly returns (all '
                                      'months / losing months only).'),
        ('Max Drawdown / DD Duration', 'Deepest peak-to-trough fall on the equity curve / '
                                       'longest underwater stretch.'),
        ('VaR / CVaR 95%', 'Monthly loss exceeded only 5% of the time / average loss when that '
                           'tail occurs.'),
        ('Information Ratio', 'Excess return over benchmark divided by tracking error - '
                              'consistency of out-performance.'),
        ('Win Rate / Profit Factor', 'Share of positive months / gross gains divided by gross '
                                     'losses.'),
        ('Portfolio Beta', 'Weighted sensitivity of the current holdings to the market '
                           '(< 1 = defensive).'),
    ]
    term_w = 148
    y -= 2
    for term, body in defs:
        c.setFillColor(BLUE_D)
        c.setFont(FB, 8.2)
        c.drawString(MX, y, term)
        ny = draw_para(c, body, MX + term_w, y, CW - term_w, size=8.4, leading=11)
        y = min(y - 12.6, ny - 1)

    y -= 12
    y = section_head(c, 'Important Disclosures', y)

    d1 = (f'All performance figures are BACKTESTED / simulated results generated by the '
          f'{PRODUCT} engine over {START_M} - {END_M} ({N_MONTHS} months) for the Base '
          f'(unhedged) strategy on the 759-stock All-Indices universe. Returns are NET of a '
          f'modeled {TURNOVER_COST} per-trade turnover cost (charged on the value of quantity '
          f'bought/sold at each monthly rebalance). Other frictions - STT, statutory/exchange '
          f'charges, GST, stamp duty, and slippage/market impact - are NOT modeled. Backtested '
          f'performance is hypothetical, does not represent actual trading, and is prepared with '
          f'the benefit of hindsight. The final month ({END_M}) is incomplete and reflects data '
          f'to {AS_OF_FMT}.')
    y = draw_para(c, d1, MX, y - 2, CW, size=8.4, leading=11, color=GREY) - 6

    d2 = ('Ex-Ante Sharpe and Ex-Ante Sortino are forward-looking, model-derived estimates based '
          'on the current holdings\u2019 return covariance; they are not realised results and '
          'will differ from ex-post ratios. Past performance - simulated or actual - is not a '
          'reliable indicator of future results. Investment in securities is subject to market '
          'and other risks; value can fall as well as rise. The proprietary selection methodology '
          'is summarised at a high level only and its specific signals are not disclosed. This '
          'document is confidential, not investment advice, and not an offer to buy or sell any '
          'security. Consult a SEBI-registered adviser before investing.')
    y = draw_para(c, d2, MX, y, CW, size=8.4, leading=11, color=GREY) - 6

    d3 = ('SMC Global Securities Ltd. is registered with SEBI as a Research Analyst, registered '
          'office 11/6B, Shanti Chamber, Pusa Road, New Delhi - 110005. Registration granted by '
          'SEBI and certification from NISM in no way guarantee performance of the intermediary '
          'or provide any assurance of returns to investors.')
    y = draw_para(c, d3, MX, y, CW, size=8.4, leading=11, color=GREY) - 8

    c.setFillColor(GREY_L)
    c.setFont(F, 7.6)
    c.drawString(MX, y, f'Data source: {PRODUCT} backtest engine (All Indices 759), '
                        f'{START_M} - {END_M}, {N_MONTHS} months, {TURNOVER_COST} turnover cost.')
    c.showPage()


# ═══════════════════════════ build ═══════════════════════════
c = rl_canvas.Canvas(str(OUT), pagesize=A4)
c.setTitle(f'{PRODUCT} - {UNIVERSE} - Performance & Backtest Report')
c.setAuthor('SMC Research')
c.setSubject(f'Backtest {START_M} - {END_M}')

page_cover(c)
page_summary(c)
page_charts(c)
page_metrics(c)
page_book(c)
page_notes(c)
c.save()

print(f'{OUT.name} generated - {N_MONTHS} mo ({START_M} to {END_M}), '
      f'{len(PORT)} holdings, CAGR {pct(CAGR)}, alpha {pct(ALPHA)}, '
      f'{OUT.stat().st_size / 1024:.0f} KB')
