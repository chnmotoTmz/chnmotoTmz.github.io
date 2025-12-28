import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
print(f"Scanning repository for non-UTF8 files under {root}...")

bad_files = []
cp932_ok = []
for p in root.rglob('*.py'):
    try:
        with open(p, 'rb') as f:
            data = f.read()
        data.decode('utf-8')
    except Exception as e_utf:
        try:
            data.decode('cp932')
            cp932_ok.append(str(p))
        except Exception as e_cp:
            bad_files.append((str(p), str(e_utf), str(e_cp)))

if not bad_files and not cp932_ok:
    print('All .py files decode as UTF-8.')
else:
    if cp932_ok:
        print('\nFiles that are not UTF-8 but decode as cp932 (possible Shift-JIS/Windows-1252 encoding):')
        for f in cp932_ok:
            print('  -', f)
    if bad_files:
        print('\nFiles that failed to decode with both UTF-8 and cp932:')
        for f, eu, ec in bad_files:
            print('  -', f)
            print('    utf8 error:', eu)
            print('    cp932 error:', ec)

# Also look for suspicious mojibake sequences (0x83 bytes) in utf8-decodable files
mojibake_files = []
for p in root.rglob('*.py'):
    try:
        with open(p, 'rb') as f:
            data = f.read()
        if b'\x83' in data:
            mojibake_files.append(str(p))
    except Exception:
        pass

if mojibake_files:
    print('\nFiles containing 0x83 bytes (common mojibake indicator):')
    for f in mojibake_files:
        print('  -', f)

print('\nScan complete.')
