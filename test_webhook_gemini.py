#!/usr/bin/env python
"""
Test webhook with Gemini-only configuration (no local LLM)
"""
import requests
import json
import time
from datetime import datetime

def send_test_webhook():
    """Send a test LINE webhook event"""
    
    webhook_url = "http://localhost:8000/api/webhook/line"
    
    # Create test event
    event = {
        "events": [
            {
                "type": "message",
                "source": {
                    "type": "user",
                    "userId": "U0082f5630775769cb2655fb503e958bb"
                },
                "timestamp": int(time.time() * 1000),
                "message": {
                    "type": "text",
                    "id": "msg_001",
                    "text": "Gemini でテスト記事を生成"
                },
                "replyToken": "nHuyWiB7yP5Zw52FIkcQT"
            }
        ]
    }
    
    print(f"\n{'='*70}")
    print(f"🧪 Sending Gemini-Only Test Webhook")
    print(f"{'='*70}")
    print(f"📝 Payload: {json.dumps(event, indent=2, ensure_ascii=False)}")
    print(f"{'='*70}\n")
    
    try:
        response = requests.post(
            webhook_url,
            json=event,
            headers={
                "Content-Type": "application/json",
                "X-Line-Signature": "test_signature_gemini_only"
            },
            timeout=10
        )
        
        print(f"✅ Response Status: {response.status_code}")
        print(f"📦 Response Body: {response.text[:500]}")
        
        if response.status_code == 200:
            print(f"\n✅ Webhook accepted successfully!")
            print(f"⏱️  Article generation started (running in background)")
            print(f"💡 Monitor Flask logs to see Gemini-only execution")
        else:
            print(f"\n❌ Webhook failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    send_test_webhook()
