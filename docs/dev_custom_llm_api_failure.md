# カスタムLLM API `/api/ask` 400 応答報告

**概要**

- 発生日: 2025-12-15
- 報告対象: ローカルのカスタムLLM API (`/api/ask`) がテスト実行時に HTTP 400 を返し、アプリのフォールバック経路が失敗しました。Cookie ベースの Gemini クライアントも初期化に失敗しているため、全体としてテキスト生成が停止します。

**影響範囲**

- `generate_text()` のカスタムLLMフォールバック経路（`CUSTOM_LLM_API_URL` / `LOCAL_GEMINI_API_URL`）が 400 を返し失敗。
- サムネイル生成の別経路には影響なし（画像生成はローカルラッパーで動作する可能性あり）。

**再現手順**

1. ローカルでカスタムラッパー（例: `http://localhost:3000`）を起動。
2. リポジトリルートで次を実行:

```powershell
$env:PYTHONPATH='.'; python scripts/test_local_gemini.py
```

3. ログに以下が出る:

- 全てのCookieで初期化に失敗しました。Gemini（Cookieベース）は利用不可です。
- Gemini Web UI呼び出し失敗: status=400, body={"code":"400","error":"Bad data: Messages cannot be empty"}

**観察された挙動**

- テスト実行時にサーバは到達しており 400 を返している（エラーメッセージは空の `messages` を指摘）。
- 手動で `{"prompt":"ping"}` を投げると成功することを確認済み（環境による差あり）。

**送信リクエスト（要確認）**

- エンドポイント: `POST /api/ask`
- ヘッダ: `Content-Type: application/json`（`Authorization` は未設定の場合あり）
- 期待されるボディ: `prompt` または `messages` のどちらを受けるかは API 仕様次第。テストでは空の `messages` が送られている可能性があります。

**サーバ応答（ログ）**

- HTTP 400
- body: `{"code":"400","error":"Bad data: Messages cannot be empty"}`

**期待する動作**

- `/api/ask` は受信したプロンプトに対して成功応答（`status: success` と `answer.text`）を返し、アプリの `generate_text()` が正常に動作すること。

> **注記:** バージョンにより、カスタムLLM の失敗時に自動的に Claude を呼び出す挙動は環境変数 `CUSTOM_LLM_FALLBACK_TO_CLAUDE` により制御できます（デフォルトは `false`）。意図しない Claude の利用を防ぐため、明示的に有効化することを推奨します。

> **追加:** `python-gemini-api` 自体は Google のページ構造変更等で認証トークン（例: `SNlM0e`）のパースに失敗することがあります。デフォルトでは当ライブラリの `auto_cookies` を試行しますが、安定性を優先する場合は `USE_PYTHON_GEMINI_API=false` を `.env` に設定してカスタム HTTP API（`CUSTOM_LLM_API_URL`）のみを利用することを推奨します。

**調査依頼（優先度: 高）**

1. サーバ側ログで問題リクエストの受信ボディを確認してください（テスト実行時の生リクエスト）。
2. `/api/ask` が期待する入力フォーマット（`prompt` / `messages`）を明確にしてください。
3. 認証が必須かどうか（Bearer トークン）を教えてください。必須ならトークンと運用手順を共有ください。
4. 入力バリデーションで 400 を返す条件を提示してください。

**添付（調査を早めるためこちらで提供可能）**

- `scripts/test_local_gemini.py` の実行ログ抜粋（実行時ログを添付予定）。
- 該当呼び出しコード: `src/services/gemini_service.py` のカスタムAPI呼び出し部分。

---

もしよければ、この Markdown をそのまま GitHub Issue に貼るか、私が代わりに Issue を作成します。Issue 作成を希望する場合はリポジトリの Issue 作成権限が必要です。
