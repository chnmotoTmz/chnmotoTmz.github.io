# Docker 立ち上げマニュアル

このプロジェクトを Docker 環境で実行し、かつホストマシン上の API (localhost:3000) と連携させるための手順書です。

## 前提条件

*   **Docker Desktop** (Windows/Mac) または **Docker Engine** (Linux) がインストールされていること。
*   ホストマシン上で、**ポート 3000** でリッスンしている API サーバー (サムネイル生成や Cookie 取得用) が起動していること。

## 構成の概要

この Docker 構成は、コンテナ内からホストマシンのローカルサーバー (`localhost:3000`) にアクセスするために、`host.docker.internal` という特別なドメインを使用しています。

*   **コンテナ**: アプリケーション (`app-chanmotocaffe`, `app-fx-channel`, `app-lang`) と データベース (`db`)
*   **ホスト**: 外部 API サーバー (Port 3000)

## 起動手順

### 1. 環境変数の設定

プロジェクトルートにある `.env.production` (または使用する環境ファイル) に必要な API キーなどが設定されていることを確認してください。

特に以下の設定は `docker-compose.yml` で自動的にホスト向きに上書きされますが、概念として理解しておいてください：

*   `CUSTOM_LLM_API_URL`: `http://host.docker.internal:3000/api/ask`
*   `CUSTOM_THUMBNAIL_API_URL`: `http://host.docker.internal:3000/api/ask`

### 2. Docker イメージのビルド

初回起動時やコードを変更した場合は、イメージのビルドが必要です。

```bash
docker-compose build
```

### 3. コンテナの起動

バックグラウンドでサービスを起動します。

```bash
docker-compose up -d
```

このコマンドにより、以下のコンテナが立ち上がります。

*   `line-gemini-hatena-chanmotocaffe`: ポート 8001
*   `line-gemini-hatena-fx-channel`: ポート 8002
*   `line-gemini-hatena-lang`: ポート 8005
*   `shared-postgres`: ポート 5432

### 4. 動作確認

コンテナが正しく起動しているか確認します。

```bash
docker-compose ps
```

全ての State が `Up` になっていることを確認してください。

ログを確認するには以下のコマンドを使用します。

```bash
docker-compose logs -f
```

## ホストマシンの API との連携について

コンテナ内のアプリケーションは、ホスト側の `localhost:3000` にアクセスするために `host.docker.internal:3000` を使用します。

### 重要な注意点: サムネイル画像の保存

ホスト側の API が画像をホストのファイルシステム（例: `Downloads` フォルダ）に保存する場合、コンテナはそのファイルに直接アクセスできません。

この問題を解決するには、`docker-compose.yml` の `volumes` 設定で、ホスト側の保存先ディレクトリをコンテナ内にマウントし、環境変数 `LOCAL_THUMBNAIL_DIR` を設定する必要があります。

**設定例 (`docker-compose.yml`):**

```yaml
services:
  app-chanmotocaffe:
    # ... 他の設定 ...
    volumes:
      # ホストのダウンロードフォルダをコンテナの /downloads にマウント
      - /Users/yourname/Downloads:/downloads
    environment:
      # コンテナ内のパスを指定
      - LOCAL_THUMBNAIL_DIR=/downloads
```
※ 現状の `docker-compose.yml` ではこの設定はコメントアウトまたは未設定の状態です。ローカル画像生成を利用する場合は、ご自身の環境に合わせて修正してください。

## 停止手順

```bash
docker-compose down
```

データを完全にリセット（データベースのボリューム削除）したい場合は `-v` オプションを付けます。

```bash
docker-compose down -v
```

## トラブルシューティング

### ホストの API に繋がらない場合

1.  ホスト側で API サーバーが `3000` 番ポートで起動しているか確認してください。
2.  Linux 環境の場合、`docker-compose.yml` に `extra_hosts: - "host.docker.internal:host-gateway"` の記述があるか確認してください（現在は設定済みです）。
3.  ファイアウォール設定で Docker ネットワークからのアクセスが許可されているか確認してください。

### データベースエラー

`Database not ready` などのエラーが出る場合は、少し待ってから再起動してみてください。初回起動時はデータベースの初期化に時間がかかる場合があります。
