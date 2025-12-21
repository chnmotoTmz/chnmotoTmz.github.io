#!/usr/bin/env python3
"""
LINE Webhookテストスクリプト
"""
import requests
import json
import hmac
import hashlib
import base64
import os

# テスト用のLINEメッセージペイロード
test_payload = {
    "events": [
        {
            "type": "message",
            "timestamp": 1630000000000,
            "source": {
                "type": "user",
                "userId": "U0082f5630775769cb2655fb503e958bb"
            },
            "replyToken": "test_reply_token",
            "message": {
                "type": "text",
                "id": "test_message_id",
                "text": "!ライフハック 　@　#推理小説風..."
            }
        }
    ]
}

def create_signature(body: str, secret: str) -> str:
    """LINE署名を作成"""
    hash_value = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return base64.b64encode(hash_value).decode()

def test_webhook():
    """Webhookテスト"""
    # 環境変数からチャンネル情報を取得
    channel_secret = os.getenv("LINE_CHANNEL_SECRET_chanmotocaffe")
    if not channel_secret:
        print("❌ LINE_CHANNEL_SECRET_chanmotocaffe が設定されていません")
        return

    # 署名を作成
    body = json.dumps(test_payload, separators=(',', ':'))
    signature = create_signature(body, channel_secret)

    # リクエスト送信
    url = "http://localhost:8000/api/webhook/line"
    headers = {
        "Content-Type": "application/json",
        "X-Line-Signature": signature
    }

    print(f"📤 Webhookテスト送信: {url}")
    print(f"📝 ペイロード: {body[:100]}...")

    try:
        response = requests.post(url, data=body, headers=headers, timeout=30)
        print(f"📥 レスポンス: {response.status_code}")
        print(f"📄 レスポンス本文: {response.text}")

        if response.status_code == 200:
            print("✅ Webhookテスト成功")
        else:
            print("❌ Webhookテスト失敗")

    except Exception as e:
        print(f"❌ リクエストエラー: {e}")

if __name__ == "__main__":
    test_webhook()