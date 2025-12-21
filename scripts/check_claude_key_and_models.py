import re
import json
import sys
from pathlib import Path
import requests

env_path = Path(__file__).resolve().parents[1] / '.env.production'
if not env_path.exists():
    print('ERROR: .env.production not found at', env_path)
    sys.exit(2)

text = env_path.read_text(encoding='utf-8')
# simple parse
m = re.search(r'^CLAUDE_API_KEY=(.+)$', text, flags=re.M)
if not m:
    print('ERROR: CLAUDE_API_KEY not found in .env.production')
    sys.exit(2)
key = m.group(1).strip()
# remove surrounding quotes if present
if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
    key = key[1:-1]

print('Using CLAUDE_API_KEY (masked):', key[:6] + '...' + key[-6:])

url = 'https://api.anthropic.com/v1/models'
headers = {'x-api-key': key}
try:
    resp = requests.get(url, headers=headers, timeout=20)
except Exception as e:
    print('Network error:', e)
    sys.exit(3)

print('HTTP', resp.status_code)
try:
    data = resp.json()
    # pretty print limited
    if isinstance(data, dict) and 'models' in data:
        models = data.get('models')
        print('Found models:', len(models))
        for m in models[:50]:
            if isinstance(m, dict):
                name = m.get('id') or m.get('name') or str(m)
            else:
                name = str(m)
            print(' -', name)
    else:
        print(json.dumps(data, indent=2)[:4000])
except Exception as e:
    print('Failed to parse JSON response:', e)
    print('Body:', resp.text[:2000])
    sys.exit(4)

if resp.status_code == 200:
    print('\nCLAUDE_API_KEY appears valid and returned model list.')
    sys.exit(0)
else:
    print('\nRequest returned non-200. The key may be invalid or lacks model access.')
    sys.exit(5)
