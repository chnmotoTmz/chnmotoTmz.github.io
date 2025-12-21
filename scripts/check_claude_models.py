import os
import requests

k = os.getenv('CLAUDE_API_KEY')
print('CLAUDE_API_KEY present:', bool(k))
headers = {'x-api-key': k or '', 'anthropic-version': '2023-06-01'}
try:
    r = requests.get('https://api.anthropic.com/v1/models', headers=headers, timeout=10)
    print('status', r.status_code)
    print(r.text)
except Exception as e:
    print('error', e)
