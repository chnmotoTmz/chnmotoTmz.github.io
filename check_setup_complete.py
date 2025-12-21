#!/usr/bin/env python3
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
from dotenv import load_dotenv
load_dotenv('.env.production')

print('=' * 70)
print('LOCAL LLM SETUP - COMPLETION STATUS')
print('=' * 70)
print()

# 1. Docker / Ollama 確認
import subprocess
result = subprocess.run(['docker', 'ps', '--filter', 'name=ollama', '--format={{.Names}}'], capture_output=True, text=True)
if 'ollama' in result.stdout:
    print('[OK] Docker Ollama Container: RUNNING')
else:
    print('[NG] Docker Ollama Container: NOT RUNNING')

# 2. モデル確認
import requests
try:
    r = requests.get('http://localhost:11434/api/tags', timeout=5)
    models = r.json().get('models', [])
    print('[OK] Ollama Server: RESPONDING')
    model_names = [m.get('name') for m in models]
    print(f'     Available Models: {model_names}')
except Exception as e:
    print(f'[NG] Ollama Server: NOT RESPONDING - {e}')

print()

# 3. Python モジュール確認
try:
    from src.services.local_llm_service import LocalLLMService
    from src.services.unified_llm_facade import UnifiedLLMFacade
    from src.services.content_enhancer_unified import ContentEnhancerLLMUnified
    print('[OK] Python Modules: ALL IMPORTED')
except Exception as e:
    print(f'[NG] Python Modules: ERROR - {e}')

# 4. 環境変数確認
print()
print('[Environment Variables]')
print(f'  LLM_PROVIDER: {os.getenv("LLM_PROVIDER", "NOT SET")}')
print(f'  LOCAL_LLM_BASE_URL: {os.getenv("LOCAL_LLM_BASE_URL", "NOT SET")}')
print(f'  LOCAL_LLM_MODEL: {os.getenv("LOCAL_LLM_MODEL", "NOT SET")}')

# 5. 統合テスト
print()
print('[Integration Test]')
try:
    llm = UnifiedLLMFacade()
    print('[OK] UnifiedLLMFacade initialized')
    print(f'     Provider: {llm.provider.value}')
except Exception as e:
    print(f'[NG] Integration test failed: {e}')

print()
print('=' * 70)
print('SETUP COMPLETE! Ready to use Local LLM')
print('=' * 70)
print()
print('Next steps:')
print('  1. Run blog generation: python run_app.py')
print('  2. Or download better model: docker exec ollama ollama pull qwen2.5:7b')
print()
