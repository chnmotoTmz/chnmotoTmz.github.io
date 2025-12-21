import os
import re

# Load minimal env vars from .env.production if present
env_file = os.path.join(os.getcwd(), '.env.production')
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r"^(GEMINI_1PSID|GEMINI_1PSIDTS|CUSTOM_LLM_API_URL|LOCAL_GEMINI_API_URL)=(.*)$", line.strip())
            if m:
                key = m.group(1)
                val = m.group(2).strip().strip('"')
                os.environ.setdefault(key, val)

from src.services.gemini_service import GeminiService

if __name__ == '__main__':
    s = GeminiService()
    print('client available:', getattr(s, '_available', False))
    try:
        res = s.generate_text('ping')
        print('generate_text result:')
        print(res)
    except Exception as e:
        print('generate_text raised:', repr(e))
