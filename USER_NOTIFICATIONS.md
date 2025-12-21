**呼び出し側向け: ローカルAPI仕様**

- **Base URL:** `http://localhost:3000`

### POST /api/ask
- 概要: プロンプトを送信し、Gemini の応答（テキスト＋画像候補）を受け取る
- Headers: `Content-Type: application/json`
- Request body:
  ```json
  { "prompt": "画像生成の説明やテキスト" }
  ```
- Success (200):
  ```json
  {
    "status":"success",
    "answer":{
      "text":"...",
      "images":[
        { "src":"https://...", "base64":null, "filename":"/downloads/gemini_image_....jpg", "downloaded": true }
      ]
    }
  }
  ```
  - `answer.text`: 取得したテキスト（あれば）
  - `images[]`: 画像候補の配列。要素は `src`, `base64`, `filename`, `downloaded` のいずれか/組合せを含み得ます。
- Errors:
  - `503` : `{ "error":"Browser extension not connected. Open Gemini tab." }`
  - `500` : `{ "error":"Timeout waiting for Gemini response" }` 等
- Notes: 呼び出し側はクッキーを送る必要はありません。

### POST /api/download
- 概要: サーバーが外部画像URLを取得して base64 を返す（CORS回避）
- Request body:
  ```json
  { "url": "https://example.com/image.jpg" }
  ```
- Success (200): `{ "status":"success", "base64":"data:image/jpeg;base64,..." }`

### POST /api/upload
- 概要: base64 を送ってサーバーに保存し、公開 URL を返す
- Request body:
  ```json
  { "filename":"optional.jpg", "base64":"data:image/png;base64,..." }
  ```
- Success (200): `{ "status":"success", "url":"http://localhost:3000/downloads/optional.jpg" }`

### GET /downloads/<filename>
- 保存済みファイルの取得（静的配信）

### 管理向け注意
- `GET /api/gemini_cookies` はサーバーの `GEMINI_*` 環境変数を返す可能性がある管理用エンドポイントです。外部へ公開しないでください。

### 運用上の重要点（ユーザーへ連絡する内容）
- 呼び出し側はクッキーを送る必要はありません。拡張がログイン済みのブラウザを操作しているため認証は拡張側/ブラウザに依存します。
- サーバーと拡張（Chromeタブ）の接続が必須です。拡張が接続されていないと `503` が返ります。拡張のコンソールに「Connected to Local Server」が出ていることを確認してください。
- 画像がブラウザのローカル保存パス（例: `C:\Users\...`）で返ってくる場合、そのままでは外部からアクセスできません。拡張で `base64` を返すか、`POST /api/upload` でサーバーに保存してください。
- `GET /api/gemini_cookies` 等の管理用エンドポイントは公開しないでください。

### 典型的な呼び出しフロー（短縮）
1. `POST /api/ask` でプロンプト送信 → 応答取得
2. 応答内 `images[0]` を確認:
   - `base64` があれば直接利用
   - `src` が返りクライアントで取得できない場合は `POST /api/download` を呼ぶ
   - `filename` が `/downloads/...` の場合は `GET /downloads/<name>` で取得
3. 必要なら `POST /api/upload` でサーバー側に保存して公開 URL を得る

---

このファイルは配布用の通知文書として作成しました。必要なら英語版や短縮版も作成します。
