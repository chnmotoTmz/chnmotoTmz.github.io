# Geminiログビューア

Gemini APIのログ（logs/posts/*.jsonl）を閲覧するためのWebアプリです。

## 起動方法

1. 必要なパッケージをインストール
   ```pwsh
   pip install -r requirements.txt
   ```
2. アプリを起動
   ```pwsh
   python app.py
   ```
3. ブラウザで `http://localhost:5000` を開く

## 機能
- ログファイル選択
- プロンプト・レスポンス・モジュール名・user_id・timestampの表示
- user_id/timestampによる絞り込み
