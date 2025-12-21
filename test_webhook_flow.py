#!/usr/bin/env python
"""Test webhook to trigger workflow with note.com posting."""
import json
import time
import requests
from datetime import datetime

# Test LINE webhook payload
test_payload = {
    "events": [
        {
            "type": "message",
            "message": {
                "type": "text",
                "text": "テストです。スマートに生活するコツはありますか？"
            },
            "replyToken": f"test_reply_{int(time.time())}",
            "source": {
                "type": "user",
                "userId": "U0082f5630775769cb2655fb503e958bb"
            },
            "timestamp": int(datetime.now().timestamp() * 1000),
            "mode": "active"
        }
    ]
}

headers = {"Content-Type": "application/json"}

try:
    print("Sending webhook request to trigger workflow...")
    response = requests.post(
        "http://localhost:8000/api/webhook/line",
        json=test_payload,
        headers=headers,
        timeout=10
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    # Wait for workflow to complete (should be fast)
    print("\nWaiting for workflow to complete...")
    time.sleep(5)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\nDone! Check the logs for thumbnail_path handling...")
