import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
changed = []
for p in sorted(root.rglob('*.py')):
    b = p.read_bytes()
    try:
        b.decode('utf-8')
        # already utf-8
        continue
    except Exception:
        try:
            s = b.decode('cp932')
            # backup
            backup = p.with_suffix(p.suffix + '.bak')
            if not backup.exists():
                backup.write_bytes(b)
            # write utf-8
            p.write_text(s, encoding='utf-8')
            changed.append(str(p))
            print('Converted', p)
        except Exception as e:
            print('Skipping (not cp932):', p, e)

print('Done. Converted files:', len(changed))
if changed:
    print('\n'.join(changed))
else:
    print('No files needed conversion')
