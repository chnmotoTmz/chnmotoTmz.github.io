# ブログ一覧と参照プロンプト 📚

このREADMEはリポジトリ内 `blogs.yml` に定義された各ブログの**特徴**と、参照される**プロンプトファイル**を一覧化したものです。
設定変更や新規ブログ追加の際の参照にしてください。

---

## 使い方 🔧
- 設定は `blogs.yml` にあります。ブログごとに `prompt_file` と `profile_prompt_file` を指定しています。
- プロンプトの実体は通常 `config/prompts/` や `data/` に配置されています。
- ブログを追加・編集する場合は `blogs.yml` を更新し、必要に応じてプロンプトファイルを追加してください。

---

## ブログ一覧（主要フィールド）

| キー | ブログ名 | hatena_id | hatena_blog_id | 説明 | prompt_file | profile_prompt_file | 主なキーワード |
|---|---|---:|---|---|---|---|---|
| `gadget_productivity` | ガジェット生産性ラボ | `motochan1969` | `lifehacking1919.hatenablog.jp` | ガジェット／生産性ツール中心のレビューとアフィリエイト | `blog_main_prompt_gadget_productivity.txt` | `blog_profile_motochan_kansai_self_deprec.txt` | ガジェット、イヤホン、モニター等 |
| `ai_music_production` | AI音楽制作スタジオ | `yamasan1969` | `hikingsong.hatenablog.jp` | AI音楽生成・DTMのレビュー。SUNO AI等に注力 | `blog_main_prompt_ai_music_production.txt` | `blog_profile_yamasan_shiba_historian_neutral.txt` | AI音楽生成、DTM、SUNO AI |
| `travel_gear` | トラベルギアレビュー | `motochan1969` | `arafo40tozan.hatenadiary.jp` | 旅行ギア・アウトドア機材のレビュー | `blog_main_prompt_travel_gear.txt` | `blog_profile_motochan_kansai_self_deprec.txt` | バックパック、スーツケース、カメラ |
| `english_learning` | English Learning Pro | `motochan1969` | `motochan1969.hatenablog.com` | 英語学習・TOEIC・オンライン英会話のレビュー | `blog_main_prompt_english_learning.txt` | `blog_profile_motochan_kansai_self_deprec.txt` | 英会話、英語アプリ、TOEIC |
| `it_engineer_philosophy` | ITエンジニアの哲学と技術 | `yamasan1969` | `yamasan1969.hatenablog.com` | 技術解説・キャリア・哲学を扱う技術系ブログ | `it_engineer_philosophy_prompt.txt` | `blog_profile_yamasan_shiba_historian_neutral.txt` | IT技術、開発、Python、AI |
| `crypto_investment` | 仮想通貨投資ラボ | `yamasan1969` | `tekunikaru.hatenadiary.jp` | 仮想通貨／投資系レビューとアフィリエイト | `blog_main_prompt_crypto_investment.txt` | `blog_profile_yamasan_shiba_historian_neutral.txt` | ビットコイン、NFT、DeFi |
| `beauty_life_hack` | ビューティーライフハック | `kaigot` | `wellness-mom-diary.hatenablog.com` | 美容家電・コスメ中心のレビュー | `blog_main_prompt_beauty_life_hack.txt` | `blog_profile_kaigot_erotic.txt` | 美容家電、スキンケア、コスメ |
| `education_review` | 教育サービスレビュー | `kaigot` | `kosodate-hub.hatenablog.com` | 教育サービス／知育玩具等のレビュー | `blog_main_prompt_education_review.txt` | `blog_profile_kaigot_erotic.txt` | オンライン学習、学習教材 |
| `daily_world_news` | 日常と世界のあいだ | `kaigot` | `kaigotmusic.hatenablog.com` | 主婦視点でニュースを解説するコラム | `blog_main_prompt_daily_world_news.txt` | `blog_profile_kaigot_erotic.txt` | ニュース解説、時事問題 |

> 注: 表中の「主なキーワード」は `blogs.yml` の `keywords` を要約したものです。

---

## 参照プロンプトの場所と運用メモ 🗂️
- プロンプトは以下のディレクトリに格納されていることが多いです。
  - `config/prompts/` — システムやテンプレートとなるプロンプト
  - `data/` — ブログ固有のプロンプトのコピーや編集版
- ブログの `prompt_file` は記事生成のメインプロンプト、`profile_prompt_file` は執筆者（ペルソナ）や文体の参照に使います。
- 変更したプロンプトはコミットして、CI やローカルでテスト実行してください（`pytest`）。

---

## 運用上の注意事項 ⚠️
- アフィリエイト情報は `FinalArticleEnricher` タスクで統合されます。外部（Rakuten）APIが空結果を返した場合は、既存のアフィリエイトブロックを復元する・プレースホルダを挿入し、`logs/affiliate_failures.log` に記録されます。
- `gemini_api_key` 等の機密情報は環境変数や `.env.*` に設定して下さい（`blogs.yml` では `${...}` で参照します）。

---

## よくある作業（短い手順）
- 新しいブログを追加する:
  1. `blogs.yml` に新しいキーと設定を追加。
  2. `config/prompts/` に `prompt_file` と `profile_prompt_file` を作成（必要なら `data/` にコピー）。
  3. テスト（`pytest`）とステージングで投稿ワークフローを確認。
- プロンプトを調整する:
  1. 該当ファイルを編集、コミット。
  2. 少量の記事生成で文体や出力形式を確認。

---

必要なら、各ブログごとに**プロンプトの抜粋（要旨）**を README に追加できます。要望があれば、抜粋を自動で抽出して追記します（例: `blog_profile_*` の先頭数行を掲示）。

---

作成: GitHub Copilot (Raptor mini (Preview))
