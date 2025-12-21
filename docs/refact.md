# 生成AI処理の実装フロー調査とリファクタリング計画

調査の結果、各処理における生成AI呼び出しの実装状況は以下の通りです。

## 1. 調査結果: 実装コンプライアンス状況

| 処理 | 要求仕様 | 現状の実装 | 判定 |
| :--- | :--- | :--- | :--- |
| **画像解析** | **ClaudeServiceを使用すること** | `GeminiService.analyze_image_from_path` は `Claude4Service` または `ClaudeService` に処理を委譲しています。 | **✅ 準拠** |
| **テキスト生成** | **python-gemini-apiを使用すること**<br>(Cookie取得: `GET http://localhost:3000/api/cookies`) | `GeminiService.generate_text` は `python-gemini-api` の `Gemini` クライアントを優先使用します。<br>初期化時に `GeminiService` 内で `fetch_cookies_from_wrapper` を呼び出し、`http://localhost:3000/api/cookies` (デフォルト値) からCookieを取得するロジックが存在します。 | **✅ 準拠** |
| **サムネイル生成** | **`localhost:3000/api/ask` を使用すること** | `ThumbnailGeneratorService` は環境変数 `CUSTOM_THUMBNAIL_API_URL` を参照します。<br>この変数が設定されていない場合、MagicHour等の外部サービスへフォールバックする実装になっています。<br>**コード上で `localhost:3000/api/ask` がデフォルト値として保証されていません。** | **⚠️ 設定依存** |

---

## 2. 詳細解析

### A. テキスト生成 (Text Generation)
*   **ファイル**: `src/services/gemini_service.py`
*   **ロジック**:
    1.  `self.gemini_client` (python-gemini-api) の初期化を試みます。
    2.  初期化されていない場合、`os.getenv('LOCAL_GEMINI_API_URL', 'http://localhost:3000/api/ask')` からルートURLを割り出し、`/api/cookies` エンドポイントを叩いてCookieを取得します。
    3.  取得したCookieを用いて `Gemini(cookies=wrapper_cookies)` を初期化します。
    4.  実際の生成時には `self.gemini_client.generate_text(prompt)` 等を呼び出します。
*   **結論**: 要求通り、Cookieを取得した上で `python-gemini-api` を使用するフローになっています。

### B. 画像解析 (Image Analysis)
*   **ファイル**: `src/services/gemini_service.py`
*   **ロジック**:
    1.  `analyze_image_from_path` メソッド内で、まず `self.claude4` (Claude 3.5 Sonnet相当) の存在を確認し、あればそれを使用します。
    2.  なければ `self.claude` (Legacy ClaudeService) を使用します。
*   **結論**: `ClaudeService` への委譲が徹底されています。

### C. サムネイル生成 (Thumbnail Generation)
*   **ファイル**: `src/services/thumbnail_generator_service.py`
*   **ロジック**:
    1.  `_generate_via_custom_api` メソッドにて `api_url` へのPOSTを実行します。
    2.  この `api_url` は `os.getenv('CUSTOM_THUMBNAIL_API_URL')` から取得されます。
    3.  環境変数が未設定の場合、このルートはスキップされ、Magic Hour API等が使用されます。
*   **課題**: 環境変数が `http://localhost:3000/api/ask` に設定されていない限り、要求仕様（`localhost:3000/api/ask`の使用）は満たされません。コードレベルでのデフォルト値設定が欠けています。

---

## 3. リファクタリング計画

サムネイル生成において、設定漏れによる意図しない外部API利用（Magic Hour等）を防ぐため、以下の改修を提案します。

### 修正方針
`ThumbnailGeneratorService` において、`CUSTOM_THUMBNAIL_API_URL` のデフォルト値をハードコード、または明示的に `http://localhost:3000/api/ask` に設定し、環境変数がなくても要求仕様のAPIを優先的に試行するように変更します。

### 具体的な変更手順
1.  **`src/services/thumbnail_generator_service.py` の修正**
    *   `generate_and_upload` メソッド内の API URL 取得ロジックを変更。
    *   変更前: `api_url = os.getenv('CUSTOM_THUMBNAIL_API_URL')`
    *   変更後: `api_url = os.getenv('CUSTOM_THUMBNAIL_API_URL', 'http://localhost:3000/api/ask')`
    *   これにより、環境変数がなくてもデフォルトで指定のローカルAPIを使用するようになります。

2.  **`docker-compose.yml` / `.env` の確認（運用対応）**
    *   念のため、本番環境の環境変数でも `CUSTOM_THUMBNAIL_API_URL=http://localhost:3000/api/ask` が明示されているか確認・追記することを推奨します。

この修正により、全てのAI処理が要求されたフロー（Claude / python-gemini-api / local api）にコードレベルで準拠することになります。


