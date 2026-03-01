# chnmotoTmz.github.io

GitHub Pages用の静的ブログリポジトリです。

## 構成
- `/posts`: Markdown形式の記事ファイル
- `/assets`: CSSや画像などの静的アセット
- `/scripts`: ビルド用のスクリプト
- `index.html`: 自動生成されるトップページ
- `*.html`: 自動生成される個別の記事ページ

## セットアップ

1. 依存関係のインストール:
   ```bash
   npm install
   ```

2. ビルド:
   ```bash
   npm run build
   ```

## 運用フロー
1. `/posts` に新しい `.md` ファイルを作成
2. `npm run build` を実行
3. 生成された HTML ファイルを git で push する

---
このプロジェクトは Hatena Blog Suite と連携して動作します。
