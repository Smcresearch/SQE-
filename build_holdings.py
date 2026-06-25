"""
Build per-month Base SIM holdings (MONTHLY_HOLDINGS) for the SQE All-Indices
site from the Port_YYYY-MM sheets in Hedge_Pro_Summary_759.xlsx.

Output: d:/SQE-host/holdings.js  ->  const MONTHLY_HOLDINGS = { "YYYY-MM": [...] }
Each holding: { s: clean symbol, w: SIM weight %, st: status, a: action, b: beta, e: erb }
Sectors are resolved on the front-end via DASHBOARD_DATA.sector_map.
"""
import json
import re
import math
import pandas as pd

SRC = 'Hedge_Pro_Summary_759.xlsx'
OUT = r'd:/SQE-host/holdings.js'

# Backtest notional per month (implied capital base). Each sheet's Qty was sized
# as weight * CAPITAL / price, so price = weight * CAPITAL / Qty. Verified stable
# at ~1 crore across stocks/months from covered historical prices.
CAPITAL = 10_000_000


def num(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def main():
    xl = pd.ExcelFile(SRC)
    port_sheets = sorted(s for s in xl.sheet_names if re.fullmatch(r'Port_\d{4}-\d{2}', s))
    holdings = {}

    for sh in port_sheets:
        month = sh.replace('Port_', '')
        # Row 0 is a title banner; the real header is on row 1.
        df = pd.read_excel(xl, sheet_name=sh, header=1)
        if 'Stock' not in df.columns or 'SIM Weight' not in df.columns:
            continue

        rows = []
        for _, r in df.iterrows():
            stock = str(r.get('Stock', '')).strip()
            if not stock or stock.lower() == 'nan':
                continue
            w = num(r.get('SIM Weight'))
            if not w or w <= 0:          # Base SIM portfolio only
                continue
            q = num(r.get('Qty'))
            price = round(w * CAPITAL / q, 2) if (q and q > 0) else None
            rows.append({
                's': stock.split('_')[0],
                'w': round(w * 100, 2),
                'p': price,
                'st': str(r.get('Status', '')).strip() or '—',
                'a': str(r.get('Action', '')).strip() or '—',
                'b': round(num(r.get('Beta')) or 0, 3),
                'e': round(num(r.get('ERB')) or 0, 3),
            })

        rows.sort(key=lambda x: x['w'], reverse=True)
        holdings[month] = rows

    payload = json.dumps(holdings, separators=(',', ':'), ensure_ascii=False)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('/* Per-month Base SIM holdings for the heatmap modal. Auto-generated. */\n')
        f.write('const MONTHLY_HOLDINGS = ' + payload + ';\n')

    total = sum(len(v) for v in holdings.values())
    print(f'[holdings] {len(holdings)} months, {total} holding rows -> {OUT}')
    sample = next(iter(holdings))
    print(f'[holdings] sample {sample}: {len(holdings[sample])} stocks, first = {holdings[sample][0] if holdings[sample] else None}')


if __name__ == '__main__':
    main()
