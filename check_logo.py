import os

# Check logo_b64.txt
b64_path = r'd:/SQE-host/logo_b64.txt'
print(f'logo_b64.txt exists: {os.path.exists(b64_path)}')
with open(b64_path, 'r') as f:
    b64 = f.read()
print(f'Base64 length: {len(b64)}')
print(f'First 80 chars: {b64[:80]}')
print(f'Last 30 chars: {b64[-30:]}')

# Check factsheet.html for the img tag
with open(r'd:/SQE-host/factsheet.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find logo img
i = html.find('class="logo"')
if i >= 0:
    # back up to <img
    start = html.rfind('<img', 0, i)
    end = html.find('>', i) + 1
    tag = html[start:end]
    print(f'\nImg tag found at {start}:{end}')
    print(f'Tag length: {len(tag)}')
    
    # Check src
    src_s = tag.find('src="') + 5
    src_e = tag.find('"', src_s)
    src_val = tag[src_s:src_e]
    print(f'src value length: {len(src_val)}')
    print(f'src starts with: {src_val[:80]}')
    
    # Try to decode the base64 part
    if 'base64,' in src_val:
        b64_part = src_val.split('base64,')[1]
        print(f'Base64 data length: {len(b64_part)}')
        import base64
        try:
            decoded = base64.b64decode(b64_part)
            print(f'Decoded size: {len(decoded)} bytes')
            print(f'First 4 bytes (magic): {decoded[:4].hex()}')
        except Exception as e:
            print(f'Decode error: {e}')
else:
    print('Logo img tag NOT found!')

# Also check if filter is the problem - the logo is webp with transparency
# Let's copy the logo directly as a file instead
import shutil
logo_src = r'C:/Users/PC2546/Desktop/SMCNEWLOGO.webp'
logo_dst = r'd:/SQE-host/smc_logo.webp'
if os.path.exists(logo_src):
    shutil.copy2(logo_src, logo_dst)
    print(f'\nCopied logo to {logo_dst} ({os.path.getsize(logo_dst)} bytes)')
else:
    print(f'Source logo not found: {logo_src}')
