# サムネイル生成タスク

このドキュメントでは、`ThumbnailGeneratorTask` モジュールについて説明します。このモジュールは、記事のサムネイル画像を生成し、記事の内容に追加する役割を果たします。

## 概要
`ThumbnailGeneratorTask` は、記事のタイトル、内容、およびサムネイル生成用のプロンプトを入力として受け取り、サムネイル画像を生成して記事の先頭に追加します。

### 主な機能
- サムネイル画像の生成
- 記事内容の先頭にサムネイルを埋め込む
- 再投稿記事の場合、既存のサムネイルを検出してスキップ
- 設定に基づくサムネイル生成の有効/無効化

## 入力
以下の入力を受け取ります：
- `title` (str): 記事のタイトル
- `content` (str): 記事の内容
- `thumbnail_prompt` (str): サムネイル生成用のプロンプト
- `enabled` (bool, オプション): サムネイル生成を有効にするかどうか（デフォルトは有効）

## 出力
以下の出力を返します：
- `enhanced_content` (str): サムネイルが追加された記事の内容
- `images` (list[str]): 生成されたサムネイル画像のURL（現在の実装では未対応の場合があります）

## 実装の詳細
### サムネイル生成の流れ
1. 入力の検証：
   - `title` と `content` が必須。
   - `thumbnail_prompt` が提供されていない場合、警告を出して処理をスキップ。

2. 再投稿記事の検出：
   - 記事内容が既にサムネイルを含む場合（例: `![...](http...)`）、サムネイル生成をスキップ。

3. サムネイル生成：
   - `ThumbnailGeneratorService` を使用して、`thumbnail_prompt` を基にサムネイル画像を生成。
   - 生成されたサムネイル画像のURLを取得。

4. 記事内容の更新：
   - サムネイル画像をMarkdown形式で記事内容の先頭に追加。

5. エラー処理：
   - サムネイル生成中にエラーが発生した場合、元の内容をそのまま返す。

### コード例
以下は、サムネイル生成の主要な部分のコード例です：
```python
try:
    print(f"🖼️ Using provided thumbnail prompt: {thumbnail_prompt[:80]}...")
    
    thumbnail_url = self.thumbnail_service.generate_and_upload(thumbnail_prompt, new_chat=inputs.get('new_chat', False))

    if not thumbnail_url:
        print("Warning: Thumbnail generation failed, returning original content.")
        return {"enhanced_content": content}

    thumbnail_markdown = f"![{title}]({thumbnail_url})\n\n"
    enhanced_content = thumbnail_markdown + content

    print(f"✅ Thumbnail successfully generated and embedded: {thumbnail_url}")
    return {"enhanced_content": enhanced_content}

except Exception as e:
    print(f"Error during thumbnail generation: {e}. Returning original content.")
    return {"enhanced_content": content}
```

## 注意事項
- `thumbnail_prompt` は、`ArticleContentGenerator` によって事前に生成され、変更せずにそのまま使用する必要があります。
- サムネイル生成が無効化されている場合、処理はスキップされます。
- 再投稿記事の場合、既存のサムネイルが検出されると生成処理はスキップされます。

## メタデータ
- **モジュール名**: ThumbnailGenerator
- **説明**: 記事のサムネイル画像を生成し、内容に追加します。
- **入力**: `title`, `content`, `thumbnail_prompt`
- **出力**: `enhanced_content`（サムネイル付き記事内容）

---

このドキュメントは、`ThumbnailGeneratorTask` の使用方法と実装の詳細を理解するための参考資料です。