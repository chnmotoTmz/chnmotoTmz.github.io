import requests, hmac, hashlib, base64, json

secret = '3bae56f66f74969fb3ecc969c88b3c85'
url = 'http://127.0.0.1:8000/api/webhook/line'
body = {
    "events": [
        {
            "type": "message",
            "message": {"type": "text", "text": "Test webhook logging"},
            "source": {"type": "user", "userId": "TESTUSER123"}
        }
    ]
}
body_s = json.dumps(body, ensure_ascii=False)
mac = hmac.new(secret.encode(), body_s.encode(), hashlib.sha256).digest()
sig = base64.b64encode(mac).decode()
headers = {'Content-Type': 'application/json', 'X-Line-Signature': sig}

r = requests.post(url, data=body_s.encode('utf-8'), headers=headers)
print('Status:', r.status_code)
print(r.text)
