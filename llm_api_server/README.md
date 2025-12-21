# LLM API Server README

## 概要
- FastAPIベースの非同期LLM APIサーバ
- テキスト生成/動画解析など用途別エンドポイント
- 非同期バッファリング（ジョブキュー）
- モデル/トークン自動切替
- セキュリティなし、textのみ返却

## 起動方法

```sh
cd llm_api_server
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

## エンドポイント

### POST /generate_text
- 入力: {"prompt": str, "model": str (optional), ...}
- 出力: {"text": job_id}（即時返答、結果は後述のGETで取得）

### GET /result/{job_id}
- 入力: job_id（POSTで返されたID）
- 出力: {"text": "PENDING" | "...生成結果..."}

## 備考
- 動画解析API等も同様に追加可能
- セキュリティなし（個人利用前提）
