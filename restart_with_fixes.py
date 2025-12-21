#!/usr/bin/env python3
"""
Fix: Run the workflow with improved BlogSelector
"""

import os
import sys
import time

# Check if Ollama is running
print("=" * 70)
print("WORKFLOW RESTART - BLOG SELECTOR TIMEOUT FIX")
print("=" * 70)
print()

# Test Ollama connection
print("[1/3] Checking Ollama connection...")
import requests
try:
    r = requests.get('http://localhost:11434/api/tags', timeout=5)
    if r.status_code == 200:
        print("✓ Ollama is running and accessible")
    else:
        print(f"✗ Ollama returned status {r.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"✗ Cannot connect to Ollama: {e}")
    print("  Please ensure Ollama is running: docker start ollama")
    sys.exit(1)

print()

# Check Phi-3 mini availability
print("[2/3] Checking Phi-3 mini model...")
try:
    r = requests.get('http://localhost:11434/api/tags', timeout=5)
    models = r.json().get('models', [])
    model_names = [m.get('name') for m in models]
    if 'phi3:mini' in model_names:
        print("✓ Phi-3 mini model is available")
    else:
        print(f"✗ Phi-3 mini not found. Available: {model_names}")
        print("  Pulling model...")
        os.system('docker exec ollama ollama pull phi3:mini')
except Exception as e:
    print(f"✗ Error checking models: {e}")

print()

# Summary
print("[3/3] Ready to start workflow")
print("-" * 70)
print()
print("🚀 Starting Flask application...")
print()
print("📋 Changes made:")
print("  1. BlogSelector now uses ローカルLLM (Phi-3 mini)")
print("  2. Added 30-second timeout protection")
print("  3. Automatic fallback to heuristic selection if timeout")
print("  4. Other tasks use Gemini (quality priority)")
print()
print("💡 To test:")
print("  1. Open http://127.0.0.1:8000")
print("  2. Send a message via LINE webhook")
print("  3. Watch logs for LLM provider messages")
print()
print("=" * 70)
print()

# Start the app
os.system('python run_app.py')
