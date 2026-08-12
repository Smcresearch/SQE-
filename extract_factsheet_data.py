"""
Extract portfolio data from data.js and generate factsheet.html
"""
import json, base64, re

with open(r'd:/SQE-host/logo_b64.txt', 'r') as f:
    logo_b64 = f.read()

with open(r'd:/SQE-host/data.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Get current portfolio
idx = content.find('current_portfolio')
bracket_depth = 0
i = content.find('[', idx)
for j in range(i, len(content)):
    if content[j] == '[': bracket_depth += 1
    elif content[j] == ']': bracket_depth -= 1
    if bracket_depth == 0:
        end_i = j
        break
port_json = content[i:end_i+1]
portfolio = json.loads(port_json)

print(f'Holdings: {len(portfolio)}')
for h in portfolio:
    sym = h['clean_symbol']
    w = h['weight']*100
    sec = h['sector']
    print(f'  {sym}: {w:.1f}% | {sec}')

# Get last_update
m = re.search(r'"last_update"\s*:\s*"([^"]+)"', content)
last_update = m.group(1) if m else '2026-08-09'

print(f'Last update: {last_update}')
