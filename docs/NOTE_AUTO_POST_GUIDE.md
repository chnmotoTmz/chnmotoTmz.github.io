# note.com 自動投稿機能

## 概要

このシステムは、生成されたブログ記事を [note.com](https://note.com) に自動的に下書きとして投稿できます。

非公式 API を使用しており、Cookie 認証をサポートしています。

## セットアップ

### 1. Cookie の取得

note.com への投稿には、ログイン状態のセッション Cookie が必要です。

#### 手動 Cookie 取得方法（推奨）

1. ブラウザで [note.com](https://note.com/login) にログイン
2. ブラウザの開発者ツールを開く（`F12` キー）
3. **コンソール (Console)** タブを開く
4. 以下のコードをコンソールに貼り付けて実行：

```javascript
console.log(JSON.stringify(
    document.cookie.split('; ').reduce((acc, c) => {
        const [k, v] = c.split('=');
        acc[k] = v;
        return acc;
    }, {})
))
```

5. コンソールに出力された JSON 文字列全体をコピー

### 2. 環境変数を設定

`.env.production` ファイルで以下を設定：

```dotenv
# note.com 非公式API認証情報
# Cookie取得方法は上記参照
NOTE_COOKIES={"_note_session":"xxxxxxx","note_user_id":"xxxxxxx",...}
```

**⚠️ セキュリティに関する注意：**
- Cookie は秘密情報です。Git リポジトリに含めないでください
- `.env.production` ファイルは `.gitignore` に追加してください
- 本番環境では環境変数で管理してください

### 3. 必要なパッケージ

メインの `requests` ライブラリは既にインストール済みです。

Selenium を使用した自動ログイン機能を使う場合（テスト用）：

```bash
pip install selenium
```

## 使用方法

### 自動ワークフロー での投稿

記事生成ワークフローの最終ステップで、自動的に note.com に投稿されます。

```json
{
  "id": "post_to_note",
  "module": "NotePost",
  "description": "Posts the article as a draft to note.com",
  "inputs": {
    "title": "${article_title}",
    "article_content": "${article_content}",
    "thumbnail_path": "${thumbnail_path}"
  }
}
```

### スタンドアロン利用

Python スクリプトから直接使用することも可能です：

```python
from src.services.note_service import NoteService
import json
import os

# Cookie を取得
with open('.env.production', 'r') as f:
    for line in f:
        if line.startswith('NOTE_COOKIES='):
            cookies_json = line.split('=', 1)[1].strip()
            cookies = json.loads(cookies_json)
            break

# NoteService を初期化
service = NoteService(cookies)

# 記事を下書き投稿
success = service.post_to_note_draft(
    title="テスト記事",
    markdown_content="# はじめに\n\nこれはテストです。",
    image_path="./thumbnail.png"
)

if success:
    print("✅ 投稿成功")
else:
    print("❌ 投稿失敗")
```

## API エンドポイント一覧

note の非公式 API で利用可能なエンドポイント：

| エンドポイント | メソッド | 説明 |
|-------------|--------|------|
| `/api/v1/text_notes` | POST | 記事を作成 |
| `/api/v1/text_notes/{id}` | PUT | 記事を更新 |
| `/api/v1/upload_image` | POST | 画像をアップロード |
| `/api/v2/creators/{username}` | GET | ユーザー情報を取得 |
| `/api/v2/creators/{username}/contents` | GET | 記事一覧を取得 |

## 仕様

### Markdown → HTML 変換

記事は自動的に Markdown から HTML に変換されます。

対応する要素：

- **見出し**: `# H1`, `## H2`, `### H3`
- **強調**: `**太字**`, `*斜体*`
- **コード**: インラインコード `` `code` `` とコードブロック
- **リスト**: `- item` (HTML `<li>` に変換)
- **改行**: 自動的に `<br>` に変換

### 画像アップロード

- **対応形式**: JPEG, PNG, GIF
- **ファイルサイズ上限**: 10MB
- **自動最適化**: 画像はサーバーで最適化される可能性があります

### レート制限

リクエスト間隔を自動調整：

- API 呼び出し間隔: 2秒
- 推奨リクエスト频度: 1分間に 10 リクエスト程度

## トラブルシューティング

### 認証エラー（401）

**原因**: Cookie が期限切れまたは無効

**解決策**:
1. ブラウザで note.com に再度ログイン
2. Cookie を再取得
3. `.env.production` を更新

### 記事作成エラー（400）

**原因**: リクエストボディの形式が不正

**確認項目**:
- Markdown テキストに HTML 特殊文字が適切にエスケープされているか
- タイトルが空でないか

### 画像アップロードエラー

**原因**: ファイルサイズが大きすぎるか形式が非対応

**確認項目**:
- ファイルサイズが 10MB 以下か
- 形式が JPEG, PNG, GIF か

### レート制限エラー（429）

**原因**: リクエストが多すぎる

**解決策**:
- リクエスト間隔を空ける
- バッチ処理の場合は間隔を 3〜5 秒に設定

## セキュリティに関する注意

⚠️ **重要な注意事項**

1. **非公式 API の使用**
   - note.com 非公式 API は予告なく仕様変更または利用不可になる可能性があります
   - 定期的に動作確認を行ってください

2. **認証情報の管理**
   - Cookie には個人情報が含まれます
   - ログファイルに Cookie を記録しないでください
   - Git リポジトリに含めないでください

3. **利用規約の遵守**
   - note.com の利用規約を遵守してください
   - サーバーに過負荷をかけないよう配慮してください
   - 短時間に大量のリクエストを送らないでください

4. **エラーハンドリング**
   - 予期しないエラーが発生する可能性があります
   - エラーハンドリングは必ず実装してください
   - ログを確認してデバッグしてください

## 活用例

### 複数プラットフォームへの同時投稿

```python
def cross_post(title, content):
    # Hatena ブログに投稿
    hatena_service.post_article(title, content)
    
    # note に投稿
    note_service.post_to_note_draft(title, content)
    
    # Zenn に投稿
    zenn_service.post_article(title, content)
```

### 定期記事投稿

```python
import schedule

def daily_post():
    today = datetime.now().strftime("%Y年%m月%d日")
    title = f"{today}の技術メモ"
    content = generate_daily_content()
    
    note_service.post_to_note_draft(title, content)

schedule.every().day.at("09:00").do(daily_post)
```

## ログ出力

すべての操作はログに記録されます。

```
INFO - Creating article: テスト記事
INFO - Article created successfully. ID: xxxxx, Key: xxxxx
INFO - Uploading image: ./thumbnail.png (12345 bytes)
INFO - Image uploaded successfully. URL: https://...
INFO - Updating article as draft: xxxxx
INFO - ✅ Article posted to note.com draft successfully!
```

## 参考リンク

- [note.com](https://note.com/)
- [Pythonでnote APIからCSV出力を試してみた](https://note.com/m316jp2/n/na3cedb64d80a)
- [noteの非公式API完全ガイド](https://note.com/masuyohasiri/n/n7c966fe553bb)

## ライセンス

このコードは本プロジェクトの一部です。MIT ライセンスの下で提供されています。
