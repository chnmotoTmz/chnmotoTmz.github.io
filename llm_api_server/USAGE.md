# LLM API Server 利用方法ドキュメント

## 概要
- FastAPIベースの非同期LLM APIサーバ
- テキスト生成（Gemini/Claude自動切替）、画像解析、動画解析（ダミー）
- 非同期バッファリング（ジョブIDで結果取得）
- セキュリティなし、textのみ返却

## 起動方法

```sh
cd llm_api_server
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

## .env.production
- プロジェクトルートの`.env.production`が自動で読み込まれます
- Gemini/Claude APIキー等はここに記載

## APIエンドポイント

### 1. テキスト生成
- `POST /generate_text`
- リクエスト:
  ```json
  { "prompt": "生成したい内容", "model": "gemini-2.5-flash" (省略可), "max_tokens": 1500, "temperature": 0.4 }
  ```
- レスポンス:
  ```json
  { "text": "<job_id>" }
  ```
- 結果取得:
  `GET /result/<job_id>` → `{ "text": "生成結果 or PENDING" }`

### 2. 画像解析
- `POST /analyze_image`
- リクエスト:
  ```json
  { "image_path": "画像ファイルの絶対パス", "prompt": "解析指示文(省略可)" }
  ```
- レスポンス:
  ```json
  { "text": "<job_id>" }
  ```
- 結果取得:
  `GET /result/<job_id>` → `{ "text": "画像説明 or PENDING" }`

### 3. 動画解析（ダミー）
- `POST /analyze_video`
- リクエスト:
  ```json
  { "video_path": "動画ファイルの絶対パス", "prompt": "解析指示文(省略可)" }
  ```
- レスポンス:
  ```json
  { "text": "<job_id>" }
  ```
- 結果取得:
  `GET /result/<job_id>` → `{ "text": "[動画解析APIは未実装です] or PENDING" }`

## 組み込み例（Python）
```python
import requests

# テキスト生成
resp = requests.post("http://localhost:8001/generate_text", json={"prompt": "こんにちはAI!"})
job_id = resp.json()["text"]
result = requests.get(f"http://localhost:8001/result/{job_id}").json()["text"]

# 画像解析
resp = requests.post("http://localhost:8001/analyze_image", json={"image_path": "/path/to/image.jpg"})
job_id = resp.json()["text"]
result = requests.get(f"http://localhost:8001/result/{job_id}").json()["text"]
```

## 注意事項
- 各APIは非同期バッファ処理のため、即時に結果は返りません。`/result/{job_id}`でポーリングしてください
- セキュリティ（認証）はありません。ローカル/信頼できる環境でのみ利用してください
- Gemini/Claude APIキーは`.env.production`で管理
- 画像/動画パスはサーバからアクセス可能な絶対パスを指定してください
