#!/usr/bin/env python3
"""
Advanced Ollama Performance & Feature Tests
"""

import requests
import json
import time

print('=' * 70)
print('ADVANCED OLLAMA TESTS (Optimized)')
print('=' * 70)
print()

model = 'phi3:mini'

# ========== Test 1: レスポンス時間計測 ==========
print('[Test 1] Response Time Analysis')
print('-' * 70)

prompts = [
    ('Simple', 'Hello'),
    ('Medium', 'Describe automation in 30 words'),
]

for label, prompt in prompts:
    start = time.time()
    r = requests.post(
        'http://localhost:11434/api/chat',
        json={
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'stream': False
        },
        timeout=300
    )
    elapsed = time.time() - start
    
    if r.status_code == 200:
        resp_len = len(r.json()['message']['content'])
        print(f'✓ {label}: {elapsed:.1f}s ({resp_len} chars)')
    else:
        print(f'✗ {label}: Error {r.status_code}')

print()

# ========== Test 2: ストリーミング vs 非ストリーミング ==========
print('[Test 2] Streaming vs Non-Streaming')
print('-' * 70)

prompt = 'List 5 programming languages'

# Non-streaming
start = time.time()
r = requests.post(
    'http://localhost:11434/api/chat',
    json={
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'stream': False
    },
    timeout=300
)
non_stream_time = time.time() - start
if r.status_code == 200:
    print(f'✓ Non-streaming: {non_stream_time:.1f}s')
else:
    print(f'✗ Non-streaming: Error {r.status_code}')

# Streaming
start = time.time()
r = requests.post(
    'http://localhost:11434/api/chat',
    json={
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'stream': True
    },
    stream=True,
    timeout=300
)
chunks = 0
for line in r.iter_lines():
    if line:
        chunks += 1
stream_time = time.time() - start
print(f'✓ Streaming: {stream_time:.1f}s ({chunks} chunks)')

print()

# ========== Test 3: 会話メモリテスト ==========
print('[Test 3] Conversation Memory (Multi-turn)')
print('-' * 70)

conversation = [
    {'role': 'user', 'content': 'What is Python used for?'},
    {'role': 'assistant', 'content': 'Data analysis, web development, automation, etc.'},
    {'role': 'user', 'content': 'Tell me more about the first use case'},
]

try:
    r = requests.post(
        'http://localhost:11434/api/chat',
        json={
            'model': model,
            'messages': conversation,
            'stream': False
        },
        timeout=300
    )
    
    if r.status_code == 200:
        response = r.json()['message']['content']
        print(f'✓ Multi-turn: {response[:80]}...')
    else:
        print(f'✗ Error {r.status_code}')
except Exception as e:
    print(f'✗ Error: {e}')

print()

# ========== Test 4: 異なる温度でのテスト ==========
print('[Test 4] Temperature Variations')
print('-' * 70)

temperatures = [0.2, 0.5, 0.9]
prompt = 'What is creativity?'

for temp in temperatures:
    try:
        r = requests.post(
            'http://localhost:11434/api/chat',
            json={
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
                'options': {'temperature': temp},
                'stream': False
            },
            timeout=300
        )
        
        if r.status_code == 200:
            response = r.json()['message']['content']
            print(f'✓ Temp {temp}: {response[:60]}...')
        else:
            print(f'✗ Temp {temp}: Error {r.status_code}')
    except Exception as e:
        print(f'✗ Temp {temp}: {e}')

print()

# ========== Test 5: モデル情報 ==========
print('[Test 5] Model Information')
print('-' * 70)

try:
    r = requests.get('http://localhost:11434/api/tags', timeout=10)
    models = r.json().get('models', [])
    
    for m in models:
        name = m.get('name')
        size = m.get('size', 0) / (1024**3)
        print(f'✓ {name}: {size:.2f}GB')
except Exception as e:
    print(f'✗ Error: {e}')

print()

# ========== Test 6: エラーハンドリング ==========
print('[Test 6] Error Handling')
print('-' * 70)

# Invalid model
try:
    r = requests.post(
        'http://localhost:11434/api/chat',
        json={
            'model': 'nonexistent-model',
            'messages': [{'role': 'user', 'content': 'test'}],
            'stream': False
        },
        timeout=10
    )
    if r.status_code != 200:
        print(f'✓ Invalid model properly rejected: {r.status_code}')
    else:
        print(f'✗ Invalid model should have failed')
except Exception as e:
    print(f'✗ Unexpected error: {e}')

# Empty prompt
try:
    r = requests.post(
        'http://localhost:11434/api/chat',
        json={
            'model': model,
            'messages': [{'role': 'user', 'content': ''}],
            'stream': False
        },
        timeout=300
    )
    if r.status_code == 200:
        print(f'✓ Empty prompt handled')
    else:
        print(f'✗ Empty prompt failed: {r.status_code}')
except Exception as e:
    print(f'✗ Error: {e}')

print()
print('=' * 70)
print('ALL TESTS COMPLETED')
print('=' * 70)
