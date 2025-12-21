import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

text_files = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        if fn.endswith('.py') or fn.endswith('.md') or fn.endswith('.txt'):
            text_files.append(Path(dirpath) / fn)

bad_utf8 = []
cp932_ok = []
other_ok = []

for p in text_files:
    try:
        data = p.read_bytes()
        data.decode('utf-8')
    except Exception as e_utf:
        # try cp932
        try:
            data.decode('cp932')
            cp932_ok.append(str(p.relative_to(ROOT)))
        except Exception as e_cp:
            # try latin1
            try:
                data.decode('latin-1')
                other_ok.append(str(p.relative_to(ROOT)))
            except Exception:
                bad_utf8.append(str(p.relative_to(ROOT)))

print('Files decode as CP932 (likely need UTF-8 conversion):')
for f in cp932_ok[:200]:
    print('  ', f)

print('\nFiles that fail UTF-8 and CP932 decoding:')
for f in bad_utf8[:200]:
    print('  ', f)

print('\nSummary:')
print('  total scanned:', len(text_files))
print('  cp932_like:', len(cp932_ok))
print('  bad_utf8:', len(bad_utf8))
print('  other_ok:', len(other_ok))
